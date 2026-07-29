"""
image_generator.py

Создает изображение меню.

Этот файл отвечает только за:

1. Создание изображения.
2. Загрузку шаблона.
3. Загрузку шрифтов.
4. Вызов функций рисования.
5. Сохранение изображения.
"""

# ============================================================
# Импорт библиотек
# ============================================================

import os

from PIL import Image, ImageDraw, ImageFont

from layout import (
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    BACKGROUND_COLOR,

    DATE_Y,

    LEFT_COLUMN_X,
    LEFT_COLUMN_Y,

    RIGHT_COLUMN_X,
    RIGHT_COLUMN_Y,

    DATE_FONT_SIZE,
    SECTION_FONT_SIZE,
    ITEM_FONT_SIZE,
    DESCRIPTION_FONT_SIZE,
)

from layout_engine import draw_column

# ============================================================
# Пути
# ============================================================

SECTION_FONT_PATH = "fonts/Montserrat-Bold.ttf"
CATEGORY_FONT_PATH = "fonts/Montserrat-Black.ttf"
ITEM_FONT_PATH = "fonts/Montserrat-Bold.ttf"
DESCRIPTION_FONT_PATH = "fonts/Montserrat-Medium.ttf"

OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "menu.png")


def load_font(path, size):
    """
    Загружает шрифт нужного размера.
    """
    return ImageFont.truetype(path, size)


def split_sections(sections):
    """
    Разделяет разделы меню
    на левую и правую колонку.
    """

    left = []
    right = []

    left_titles = {
        "САЛАТЫ",
        "ГОРЯЧИЕ БЛЮДА",
        "ГАРНИРЫ",
    }

    for section in sections:

        if section["title"] in left_titles:
            left.append(section)
        else:
            right.append(section)

    return left, right


def generate_image(data):
    """
    Создает изображение меню.
    """

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ============================================================
    # Загружаем шаблон
    # ============================================================

    template_path = "Templates/default.png"

    if os.path.exists(template_path):

        image = Image.open(template_path).convert("RGB")

        # Если размер шаблона отличается —
        # автоматически приводим его к нужному размеру.

        image = image.resize(
            (IMAGE_WIDTH, IMAGE_HEIGHT)
        )

    else:

        image = Image.new(
            "RGB",
            (IMAGE_WIDTH, IMAGE_HEIGHT),
            BACKGROUND_COLOR,
        )

    draw = ImageDraw.Draw(image)

    # Загружаем шрифты

    date_font = load_font(
        SECTION_FONT_PATH,
        DATE_FONT_SIZE,
    )

    section_font = load_font(
        CATEGORY_FONT_PATH,
        SECTION_FONT_SIZE,
    )

    item_font = load_font(
        ITEM_FONT_PATH,
        ITEM_FONT_SIZE,
    )

    description_font = load_font(
        DESCRIPTION_FONT_PATH,
        DESCRIPTION_FONT_SIZE,
    )

    # Вычисляем ширину даты
    text_width = draw.textlength(
        data["date"],
        font=date_font,
    )

    # Центрируем по горизонтали
    date_x = (IMAGE_WIDTH - text_width) / 2

    # Рисуем дату
    draw.text(
        (date_x, DATE_Y),
        data["date"],
        font=date_font,
        fill="#222222",
    )

    # Делим разделы на две колонки
    left_sections, right_sections = split_sections(
        data["sections"]
    )

    # Левая колонка

    draw_column(
        draw=draw,
        sections=left_sections,
        x=LEFT_COLUMN_X,
        y=LEFT_COLUMN_Y,
        title_font=section_font,
        item_font=item_font,
        description_font=description_font,
    )

    # Правая колонка

    draw_column(
        draw=draw,
        sections=right_sections,
        x=RIGHT_COLUMN_X,
        y=RIGHT_COLUMN_Y,
        title_font=section_font,
        item_font=item_font,
        description_font=description_font,
    )

    image.save(OUTPUT_FILE)

    return OUTPUT_FILE
