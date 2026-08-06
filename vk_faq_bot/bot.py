"""Запуск VK FAQ-бота через Bots Long Poll API."""

import logging
import json
import re
import time
from collections import defaultdict, deque
from pathlib import Path
from random import randint

import vk_api
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll

from config import KNOWLEDGE_BASE_PATH, VK_GROUP_ID, VK_GROUP_TOKEN
from llm import answer_question


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 4_000
MAX_SEEN_MESSAGES = 1_000
MAX_HISTORY_MESSAGES = 6
MUTE_DURATION_SECONDS = 24 * 60 * 60
HANDOFF_MESSAGE = (
    "Ожидайте ответа менеджера в сообщениях или позвоните нам: 560-550 или "
    "+7 (991) 409-61-54."
)
FALLBACK_MESSAGE = HANDOFF_MESSAGE
BOOKING_MESSAGE = (
    "Для бронирования, изменения или отмены брони, пожалуйста, позвоните нам: "
    "560-550 или +7 (991) 409-61-54. При звонке сообщите дату, время и "
    "количество гостей."
)
BOOKING_KEYWORDS = ("брон", "заброн", "столик", "заказать стол")
SILENT_USERS_PATH = Path(__file__).resolve().parent / "silent_users.json"
MUTED_DIALOGS_PATH = Path(__file__).resolve().parent / "muted_dialogs.json"
OWN_BEER_MESSAGE = (
    "С разрешения администратора можно принести свой алкоголь, но пиво "
    "приносить нельзя. Минимальная сумма заказа — 2000 ₽ на человека."
)


def load_knowledge_base() -> str:
    """Загружает FAQ перед обработкой сообщения, чтобы изменения применялись сразу."""

    try:
        text = Path(KNOWLEDGE_BASE_PATH).read_text(encoding="utf-8").strip()
    except OSError as error:
        raise RuntimeError(f"Не удалось прочитать базу знаний: {KNOWLEDGE_BASE_PATH}") from error

    if not text:
        raise RuntimeError("База знаний пуста")
    return text


def send_message(vk, peer_id: int, text: str) -> None:
    """Отправляет ответ с уникальным random_id, требуемым VK API."""

    vk.messages.send(peer_id=peer_id, message=text, random_id=randint(1, 2_147_483_647))


def is_booking_request(text: str) -> bool:
    """Определяет запросы о брони, которые нельзя передавать нейросети."""

    normalized = text.lower()
    return any(keyword in normalized for keyword in BOOKING_KEYWORDS)


def is_unclear_message(text: str) -> bool:
    """Отсекает короткие цифровые коды и фразы без понятного вопроса."""

    normalized = text.lower().strip()
    if not re.search(r"[а-яё]", normalized):
        return True

    # Например, «41 обед» — это не вопрос о бизнес-ланче. Не пытаемся
    # угадать смысл номера, артикула или внутренней пометки гостя.
    return bool(re.search(r"\b\d+\s*(?:обед|ланч)\b", normalized))


def is_own_beer_question(text: str) -> bool:
    """Находит вопрос о принесённом гостем пиве, для которого ответ однозначен."""

    normalized = text.lower()
    return "пиво" in normalized and any(
        marker in normalized for marker in ("принест", "свой", "своё")
    )


def is_handoff_response(text: str) -> bool:
    """Распознаёт передачу менеджеру даже при отличиях в пробелах или пунктуации."""

    normalized = " ".join(text.lower().split())
    return "ожидайте ответа менеджера" in normalized and "560-550" in normalized


def is_duplicate_message(
    message: dict, seen_ids: set[int], seen_order: deque[int]
) -> bool:
    """Отбрасывает повторную доставку одного и того же события Long Poll."""

    message_id = message.get("id")
    if not isinstance(message_id, int):
        return False
    if message_id in seen_ids:
        return True

    if len(seen_order) == MAX_SEEN_MESSAGES:
        seen_ids.remove(seen_order.popleft())
    seen_order.append(message_id)
    seen_ids.add(message_id)
    return False


def load_silent_user_ids() -> set[int]:
    """Возвращает VK ID гостей, для которых автоответы отключены."""

    try:
        data = json.loads(SILENT_USERS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("ожидается JSON-массив")
        return {int(user_id) for user_id in data}
    except (OSError, ValueError, json.JSONDecodeError) as error:
        logger.error("Не удалось прочитать список silent_users.json: %s", error)
        return set()


def load_muted_dialogs() -> dict[int, float]:
    """Загружает временно отключённые диалоги и убирает истёкшие записи."""

    try:
        data = json.loads(MUTED_DIALOGS_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("ожидается JSON-объект")
        now = time.time()
        return {
            int(peer_id): float(deadline)
            for peer_id, deadline in data.items()
            if float(deadline) > now
        }
    except (OSError, ValueError, json.JSONDecodeError) as error:
        logger.error("Не удалось прочитать список muted_dialogs.json: %s", error)
        return {}


def save_muted_dialogs(muted_dialogs: dict[int, float]) -> None:
    """Сохраняет временный режим тишины, чтобы он переживал перезапуск."""

    MUTED_DIALOGS_PATH.write_text(
        json.dumps(muted_dialogs, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def is_dialog_muted(peer_id: int, muted_dialogs: dict[int, float]) -> bool:
    """Проверяет, действует ли 24-часовая пауза для диалога."""

    deadline = muted_dialogs.get(peer_id)
    if deadline is None:
        return False
    if deadline > time.time():
        return True

    del muted_dialogs[peer_id]
    save_muted_dialogs(muted_dialogs)
    return False


def mute_dialog(peer_id: int, muted_dialogs: dict[int, float]) -> None:
    """Передаёт диалог менеджеру на 24 часа."""

    muted_dialogs[peer_id] = time.time() + MUTE_DURATION_SECONDS
    save_muted_dialogs(muted_dialogs)


def main() -> None:
    """Слушает новые личные сообщения сообщества и отвечает на них."""

    vk_session = vk_api.VkApi(token=VK_GROUP_TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, VK_GROUP_ID)
    seen_message_ids: set[int] = set()
    seen_message_order: deque[int] = deque()
    muted_dialogs = load_muted_dialogs()
    histories: dict[int, deque[dict[str, str]]] = defaultdict(
        lambda: deque(maxlen=MAX_HISTORY_MESSAGES)
    )

    logger.info("VK FAQ-бот запущен")
    for event in longpoll.listen():
        if event.type != VkBotEventType.MESSAGE_NEW:
            continue

        message = event.object.message
        if message.get("from_id", 0) <= 0:
            continue
        if message["from_id"] in load_silent_user_ids():
            continue
        if is_duplicate_message(message, seen_message_ids, seen_message_order):
            continue

        peer_id = message["peer_id"]
        # Отвечаем только в личных сообщениях сообщества, а не в общих чатах.
        if peer_id != message["from_id"]:
            continue
        if is_dialog_muted(peer_id, muted_dialogs):
            continue

        question = message.get("text", "").strip()
        if not question:
            send_message(vk, peer_id, "Напишите вопрос текстом — я постараюсь помочь.")
            continue
        if len(question) > MAX_MESSAGE_LENGTH:
            send_message(vk, peer_id, "Сообщение слишком длинное. Сократите вопрос до 4 000 символов.")
            continue
        if is_unclear_message(question):
            histories[peer_id].clear()
            mute_dialog(peer_id, muted_dialogs)
            send_message(vk, peer_id, HANDOFF_MESSAGE)
            continue
        if is_own_beer_question(question):
            send_message(vk, peer_id, OWN_BEER_MESSAGE)
            continue
        if is_booking_request(question):
            # Не сохраняем попытку брони: её детали не должны стать контекстом
            # для нейросети и выглядеть как подтверждённая заявка.
            histories[peer_id].clear()
            send_message(vk, peer_id, BOOKING_MESSAGE)
            continue

        try:
            knowledge_base = load_knowledge_base()
            response = answer_question(question, knowledge_base, list(histories[peer_id]))
        except Exception:
            logger.exception("Не удалось обработать сообщение из диалога %s", peer_id)
            send_message(vk, peer_id, FALLBACK_MESSAGE)
            continue

        if is_handoff_response(response):
            histories[peer_id].clear()
            mute_dialog(peer_id, muted_dialogs)
            send_message(vk, peer_id, response)
            continue

        histories[peer_id].append({"role": "user", "content": question})
        histories[peer_id].append({"role": "assistant", "content": response})
        send_message(vk, peer_id, response)


if __name__ == "__main__":
    main()
