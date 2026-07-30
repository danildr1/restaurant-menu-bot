"""
bot.py

Главный файл Telegram-бота.

Он отвечает за:
1. Запуск бота.
2. Получение сообщений.
3. Передачу текста в parser.py.
4. Генерацию изображения.
5. Отправку изображения пользователю.
"""

# ============================================================
# Импорт стандартных библиотек
# ============================================================

import logging
import os
import asyncio
from contextlib import suppress
from uuid import uuid4
from llm import improve_menu, improve_menu_from_image

from dotenv import load_dotenv

# ============================================================
# Импорт Telegram
# ============================================================

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ============================================================
# Импорт наших модулей
# ============================================================

from parser import parse_menu
from image_generator import generate_image
from text_normalizer import normalize_menu_text

# ============================================================
# Загрузка переменных окружения
# ============================================================

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("В файле .env отсутствует BOT_TOKEN")

# ============================================================
# Настройка логирования
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

WAITING_CAT_URL = "https://cataas.com/cat/says/Думою..."



# ============================================================
# Команда /start
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляется при вводе команды /start.
    """

    await update.message.reply_text(
        "Привет!\n\n"
        "Пришли текст или фотографию бизнес-ланча — я создам изображение меню.",
        reply_markup=ReplyKeyboardRemove(),
    )


# ============================================================
# Получение исходного текста
# ============================================================

async def get_menu_input(update: Update) -> tuple[str, bool]:
    """Возвращает текст и признак, что фото уже обработано vision-моделью."""

    if update.message.text:
        return update.message.text, False

    photo = update.message.photo[-1]
    photo_file = await photo.get_file()
    image_bytes = await photo_file.download_as_bytearray()

    menu_text = await asyncio.to_thread(
        improve_menu_from_image,
        bytes(image_bytes),
    )
    return menu_text, True


# ============================================================
# Обработка сообщения с меню
# ============================================================

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Нормализует текст меню и сразу создаёт изображение.
    """

    progress_message = None

    try:
        progress_message = await update.message.reply_photo(
            photo=f"{WAITING_CAT_URL}?v={uuid4().hex}",
            caption=(
                "🐈 Разбираю меню… Это может занять немного времени: "
                "на платную нейросеть денег пока не накопили, поэтому наша "
                "старается особенно вдумчиво."
            ),
        )
    except Exception:
        logger.warning("Не удалось отправить котомем", exc_info=True)

    async def show_slow_progress():
        """Шутливо сообщает о долгом ответе LLM без нового уведомления."""

        await asyncio.sleep(10)

        try:
            await progress_message.edit_caption(
                "😅 Едрить там менюха… всей кухней перелопачиваем текст. "
                "Ещё немного!"
            )

            await asyncio.sleep(20)
            await progress_message.edit_caption(
                "🫠 Ты че туда засунул?"
                "Мы уже вспотели это читать!"
            )
        except Exception:
            logger.warning("Не удалось обновить подпись котомема", exc_info=True)

    slow_progress_task = (
        asyncio.create_task(show_slow_progress()) if progress_message else None
    )

    try:
        source_text, is_vision_result = await get_menu_input(update)
    except Exception:
        logger.exception("Не удалось получить текст меню")

        if slow_progress_task:
            slow_progress_task.cancel()
            with suppress(asyncio.CancelledError):
                await slow_progress_task

        if progress_message:
            try:
                await progress_message.delete()
            except Exception:
                logger.warning("Не удалось удалить котомем после ошибки", exc_info=True)

        await update.message.reply_text(
            "❌ Не смог прочитать фотографию.\n\n"
            "Пришли её ещё раз, но без картошки на объективе 😼",
        )
        return

    try:
        if is_vision_result:
            improved_text = source_text
        else:
            improved_text = await asyncio.to_thread(
                improve_menu,
                source_text,
            )
    except Exception as e:
        print(f"LLM error: {e}")
        improved_text = source_text
    finally:
        if slow_progress_task:
            slow_progress_task.cancel()
            with suppress(asyncio.CancelledError):
                await slow_progress_task

    text, corrections = normalize_menu_text(improved_text)

    print("===== AFTER LLM =====")
    print(improved_text)
    print("=====================")

    try:
        if progress_message:
            await progress_message.edit_caption(
                "🎨 Текст разобран. Рисую меню — осталось чуть-чуть!"
            )

        data = parse_menu(text)
        image_path = generate_image(data)

        with open(image_path, "rb") as photo:
            await update.message.reply_photo(photo=photo)

        if progress_message:
            await progress_message.edit_caption("✅ Готово! Меню подано.")

        if corrections:
            corrections_text = "\n".join(f"• {item}" for item in corrections[:10])
            await update.message.reply_text(
                "Изменения при подготовке текста:\n" + corrections_text,
            )

        await update.message.reply_text("Давай следующую менюху 😼")

    except Exception:
        logger.exception("Ошибка при обработке меню")

        if progress_message:
            try:
                await progress_message.delete()
            except Exception:
                logger.warning("Не удалось удалить котомем после ошибки", exc_info=True)

        await update.message.reply_text(
            "❌ Лох, он и в Африке лох. Произошла ошибка.\n\n"
            "Иди проверь, что ты нам вообще отправил, и попробуй ещё раз",
        )


# ============================================================
# Точка входа
# ============================================================

def main():
    """
    Запускает Telegram-бота.
    """

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        MessageHandler(
            (filters.TEXT & ~filters.COMMAND) | filters.PHOTO,
            menu,
        )
    )

    logger.info("Бот запущен")

    app.run_polling()


if __name__ == "__main__":
    main()
