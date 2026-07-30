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
from dataclasses import replace

from PIL import Image, ImageDraw, ImageFont

from layout import (
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    BACKGROUND_COLOR,
    get_layout,
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
    Распределяет разделы между колонками, сохраняя привычный порядок
    и не допуская переполнения одной из них.
    """

    left = []
    right = []

    column_weight = {
        "left": 0,
        "right": 0,
    }

    preferred_column = {
        "САЛАТЫ": "left",
        "ГОРЯЧИЕ БЛЮДА": "left",
        "СУПЫ": "right",
    }

    def section_weight(section):
        """Приблизительная высота раздела в строках текста."""

        weight = 2  # заголовок и отступ после раздела

        for item in section["items"]:
            weight += 1 + len(item["name"]) / 22
            weight += len(item.get("description", "")) / 30

        return weight

    for section in sections:
        title = section["title"]
        target = preferred_column.get(title)

        if target is None:
            target = min(column_weight, key=column_weight.get)

        if target == "left":
            left.append(section)
        else:
            right.append(section)

        column_weight[target] += section_weight(section)

    return left, right


def menu_content_weight(sections):
    """Оценивает плотность меню по количеству и длине текстовых блоков."""

    weight = 0

    for section in sections:
        for item in section["items"]:
            weight += 1
            weight += len(item["name"]) / 45
            weight += len(item.get("description", "")) / 70

    return weight


def fit_section_spacing(
    image,
    left_sections,
    right_sections,
    title_font,
    item_font,
    description_font,
    layout,
):
    """Сжимает отступы, сохраняя между категориями минимальный воздух."""

    safe_bottom = round(image.height * 0.75)
    minimum_spacing = max(12, round(image.width * 0.0167))

    def column_bottom(candidate_layout):
        measure_image = Image.new("RGB", image.size)
        measure_draw = ImageDraw.Draw(measure_image)

        left_bottom = draw_column(
            draw=measure_draw,
            sections=left_sections,
            x=candidate_layout.left_column_x,
            y=candidate_layout.columns_y,
            title_font=title_font,
            item_font=item_font,
            description_font=description_font,
            column_width=candidate_layout.left_column_width,
            layout=candidate_layout,
        )
        right_bottom = draw_column(
            draw=measure_draw,
            sections=right_sections,
            x=candidate_layout.right_column_x,
            y=candidate_layout.columns_y,
            title_font=title_font,
            item_font=item_font,
            description_font=description_font,
            column_width=candidate_layout.right_column_width,
            layout=candidate_layout,
        )
        return max(left_bottom, right_bottom)

    if column_bottom(layout) <= safe_bottom:
        return layout, True

    low = min(minimum_spacing, layout.section_spacing)
    high = layout.section_spacing

    if column_bottom(replace(layout, section_spacing=low)) > safe_bottom:
        return replace(layout, section_spacing=low), False

    while low < high:
        middle = (low + high + 1) // 2
        candidate = replace(layout, section_spacing=middle)

        if column_bottom(candidate) <= safe_bottom:
            low = middle
        else:
            high = middle - 1

    return replace(layout, section_spacing=low), True


def load_content_fonts(layout):
    """Загружает шрифты разделов и позиций для заданного масштаба."""

    return (
        load_font(CATEGORY_FONT_PATH, layout.section_font_size),
        load_font(ITEM_FONT_PATH, layout.item_font_size),
        load_font(DESCRIPTION_FONT_PATH, layout.description_font_size),
    )


def scale_content_fonts(layout, scale):
    """Уменьшает шрифты меню, не трогая дату и минимальные отступы."""

    return replace(
        layout,
        section_font_size=round(layout.section_font_size * scale),
        item_font_size=round(layout.item_font_size * scale),
        description_font_size=round(layout.description_font_size * scale),
    )


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

    else:

        image = Image.new(
            "RGB",
            (IMAGE_WIDTH, IMAGE_HEIGHT),
            BACKGROUND_COLOR,
        )

    draw = ImageDraw.Draw(image)
    layout = get_layout(
        *image.size,
        content_weight=menu_content_weight(data["sections"]),
    )

    # Загружаем шрифты

    date_font = load_font(
        SECTION_FONT_PATH,
        layout.date_font_size,
    )

    left_sections, right_sections = split_sections(data["sections"])

    # Сначала сжимаем только расстояния между категориями. Если этого
    # недостаточно, постепенно уменьшаем шрифты позиций и составов.
    base_layout = layout
    for font_scale in (1, 0.95, 0.9, 0.85, 0.8):
        candidate_layout = scale_content_fonts(base_layout, font_scale)
        section_font, item_font, description_font = load_content_fonts(
            candidate_layout
        )
        candidate_layout, fits = fit_section_spacing(
            image,
            left_sections,
            right_sections,
            section_font,
            item_font,
            description_font,
            candidate_layout,
        )

        layout = candidate_layout
        if fits:
            break

    # Вычисляем ширину даты
    text_width = draw.textlength(
        data["date"],
        font=date_font,
    )

    # Центрируем по горизонтали
    date_x = (image.width - text_width) / 2

    # Рисуем дату
    draw.text(
        (date_x, layout.date_y),
        data["date"],
        font=date_font,
        fill=layout.text_color,
    )

    # Левая колонка

    draw_column(
        draw=draw,
        sections=left_sections,
        x=layout.left_column_x,
        y=layout.columns_y,
        title_font=section_font,
        item_font=item_font,
        description_font=description_font,
        column_width=layout.left_column_width,
        layout=layout,
    )

    # Правая колонка

    draw_column(
        draw=draw,
        sections=right_sections,
        x=layout.right_column_x,
        y=layout.columns_y,
        title_font=section_font,
        item_font=item_font,
        description_font=description_font,
        column_width=layout.right_column_width,
        layout=layout,
    )

    image.save(OUTPUT_FILE)

    return OUTPUT_FILE
