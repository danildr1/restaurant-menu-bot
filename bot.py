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
from turtle import update
from LLM import improve_menu

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
CONFIRM_MENU_BUTTON = "✅ Подтвердить меню"
CANCEL_MENU_BUTTON = "Отменить"

KEYBOARD = ReplyKeyboardMarkup(
    [[GENERATE_MENU_BUTTON]],
    resize_keyboard=True,
)

PREVIEW_KEYBOARD = ReplyKeyboardMarkup(
    [[CONFIRM_MENU_BUTTON, CANCEL_MENU_BUTTON]],
    resize_keyboard=True,
    one_time_keyboard=True,
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

    context.user_data.pop("pending_menu_text", None)

    await update.message.reply_text(
        "Отправь текст бизнес-ланча, и я создам изображение меню."
    )


# ============================================================
# Обработка сообщения с меню
# ============================================================

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Нормализует текст меню и показывает его для подтверждения.
    """

    try:
        improved_text = await asyncio.to_thread(
            improve_menu,
            update.message.text
        )
    except Exception as e:
        print(f"LLM error: {e}")
        improved_text = update.message.text

    text, corrections = normalize_menu_text(improved_text)

    print("===== AFTER LLM =====")
    print(improved_text)
    print("=====================")

    context.user_data["pending_menu_text"] = text

    corrections_text = "\n".join(f"• {item}" for item in corrections[:10])
    message = "Проверь исправленный текст и подтверди создание меню:\n\n" + text

    if corrections_text:
        message += "\n\nИсправления и рекомендации:\n" + corrections_text

    await update.message.reply_text(
        message,
        reply_markup=PREVIEW_KEYBOARD,
    )


async def confirm_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создаёт изображение меню из подтверждённого текста."""

    text = context.user_data.pop("pending_menu_text", None)

    if not text:
        await update.message.reply_text(
            "Нет текста для подтверждения. Отправь меню ещё раз.",
            reply_markup=KEYBOARD,
        )
        return

    try:
        data = parse_menu(text)
        image_path = generate_image(data)

        with open(image_path, "rb") as photo:
            await update.message.reply_photo(photo=photo, reply_markup=KEYBOARD)

    except Exception:
        logger.exception("Ошибка при обработке меню")

        await update.message.reply_text(
            "❌ Не удалось создать меню.\n\n"
            "Проверьте текст и попробуйте ещё раз.",
            reply_markup=KEYBOARD,
        )


async def cancel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет создание изображения из предварительного текста."""

    context.user_data.pop("pending_menu_text", None)

    await update.message.reply_text(
        "Создание меню отменено.",
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
            filters.Regex(f"^{re.escape(CONFIRM_MENU_BUTTON)}$"),
            confirm_menu,
        )
    )

    app.add_handler(
        MessageHandler(
            filters.Regex(f"^{re.escape(CANCEL_MENU_BUTTON)}$"),
            cancel_menu,
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
