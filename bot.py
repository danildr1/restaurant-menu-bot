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
from multiprocessing import context
import os
import re
import asyncio
from contextlib import suppress
from uuid import uuid4
from turtle import update
from llm import improve_menu

from dotenv import load_dotenv

# ============================================================
# Импорт Telegram
# ============================================================

from telegram import ReplyKeyboardMarkup, Update
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

GENERATE_MENU_BUTTON = "Сгенерировать меню по тексту"
WAITING_CAT_URL = "https://cataas.com/cat/says/Думою..."

KEYBOARD = ReplyKeyboardMarkup(
    [[GENERATE_MENU_BUTTON]],
    resize_keyboard=True,
)



# ============================================================
# Команда /start
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отправляется при вводе команды /start.
    """

    await update.message.reply_text(
        "Привет!\n\n"
        "Нажми «Сгенерировать меню по тексту», затем отправь текст бизнес-ланча.",
        reply_markup=KEYBOARD,
    )


# ============================================================
# Кнопка генерации меню
# ============================================================

async def request_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Просит пользователя отправить текст меню.
    """

    await update.message.reply_text(
        "Отправь текст бизнес-ланча, и я создам изображение меню."
    )


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
                "🐈 Думаю над текстом… Это может занять немного времени: "
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
        improved_text = await asyncio.to_thread(
            improve_menu,
            update.message.text
        )
    except Exception as e:
        print(f"LLM error: {e}")
        improved_text = update.message.text
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
            await update.message.reply_photo(photo=photo, reply_markup=KEYBOARD)

        if progress_message:
            await progress_message.edit_caption("✅ Готово! Меню подано.")

        if corrections:
            corrections_text = "\n".join(f"• {item}" for item in corrections[:10])
            await update.message.reply_text(
                "Изменения при подготовке текста:\n" + corrections_text,
                reply_markup=KEYBOARD,
            )

    except Exception:
        logger.exception("Ошибка при обработке меню")

        await update.message.reply_text(
            "❌ Лох, он и в Африке лох. Произошла ошибка.\n\n"
            "Иди проверь, что ты нам вообще отправил, и попробуй ещё раз",
            reply_markup=KEYBOARD,
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
            filters.Regex(f"^{re.escape(GENERATE_MENU_BUTTON)}$"),
            request_menu,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            menu,
        )
    )

    logger.info("Бот запущен")

    app.run_polling()


if __name__ == "__main__":
    main()
