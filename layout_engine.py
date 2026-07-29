"""
layout_engine.py

Движок рисования меню.

Этот файл ничего не знает о Telegram,
parser.py или image_generator.py.

Он умеет только рисовать.
"""

from PIL import ImageDraw

from layout import (
    COLUMN_WIDTH,
    TEXT_COLOR,
    DESCRIPTION_COLOR,
    LINE_HEIGHT,
    ITEM_SPACING,
    SECTION_SPACING,
)


# ============================================================
# Перенос длинного текста
# ============================================================

def wrap_text(draw, text, font, width):
    """
    Разбивает длинную строку
    на несколько строк.
    """

    if not text:
        return []

    words = text.split()

    lines = []

    current = words[0]

    for word in words[1:]:

        candidate = current + " " + word

        if draw.textlength(candidate, font=font) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)

    return lines


# ============================================================
# Одно блюдо
# ============================================================

def draw_item(
    draw,
    item,
    x,
    y,
    item_font,
    description_font,
):
    """
    Рисует одно блюдо.
    """

    # ---------- Название блюда ----------

    title = item["name"]

    if item.get("price"):
        title += f" {item['price']}"

    title_lines = wrap_text(
        draw,
        title,
        item_font,
        COLUMN_WIDTH,
    )

    for line in title_lines:

        draw.text(
            (x, y),
            line,
            fill=TEXT_COLOR,
            font=item_font,
        )

        y += LINE_HEIGHT

    # ---------- Состав ----------

    if item["description"]:

        description_lines = wrap_text(
            draw,
            item["description"],
            description_font,
            COLUMN_WIDTH,
        )

        for line in description_lines:

            draw.text(
                (x, y),
                line,
                fill=DESCRIPTION_COLOR,
                font=description_font,
            )

            y += LINE_HEIGHT - 6

    # ---------- Отступ ----------

    y += ITEM_SPACING

    return y


# ============================================================
# Раздел
# ============================================================

def draw_section(
    draw,
    section,
    x,
    y,
    title_font,
    item_font,
    description_font,
):
    """
    Рисует раздел меню.
    """

    draw.text(
        (x, y),
        section["title"],
        fill=TEXT_COLOR,
        font=title_font,
    )

    y += LINE_HEIGHT + 12

    for item in section["items"]:

        y = draw_item(
            draw=draw,
            item=item,
            x=x,
            y=y,
            item_font=item_font,
            description_font=description_font,
        )

    y += SECTION_SPACING

    return y


# ============================================================
# Колонка
# ============================================================

def draw_column(
    draw,
    sections,
    x,
    y,
    title_font,
    item_font,
    description_font,
):
    """
    Рисует целую колонку меню.
    """

    current_y = y

    for section in sections:

        current_y = draw_section(
            draw=draw,
            section=section,
            x=x,
            y=current_y,
            title_font=title_font,
            item_font=item_font,
            description_font=description_font,
        )

    return current_y
