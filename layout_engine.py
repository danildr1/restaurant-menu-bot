"""Движок рисования меню."""


def wrap_text(draw, text, font, width):
    """Разбивает текст на строки, которые помещаются в колонку."""

    if not text:
        return []

    words = text.split()
    lines = []
    current = words[0]

    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word

    lines.append(current)
    return lines


def text_line_height(font, spacing):
    """Высота строки на основе фактического шрифта."""

    bbox = font.getbbox("Аy")
    return bbox[3] - bbox[1] + spacing


def draw_item(draw, item, x, y, item_font, description_font, column_width, layout):
    """Рисует блюдо и, при наличии, его состав."""

    title = item["name"].strip()
    if title.startswith(("- ", "– ", "— ")):
        title = title[2:].lstrip()

    marker_radius = max(3, item_font.size // 11)
    text_indent = marker_radius * 4
    text_x = x + text_indent
    text_width = column_width - text_indent

    draw.ellipse(
        (
            x,
            y + item_font.size * 0.48 - marker_radius,
            x + marker_radius * 2,
            y + item_font.size * 0.48 + marker_radius,
        ),
        fill=layout.section_color,
    )

    title_lines = wrap_text(draw, title, item_font, text_width)

    if item.get("price"):
        price = item["price"]
        last_line_with_price = f"{title_lines[-1]} {price}"

        if draw.textlength(last_line_with_price, font=item_font) <= text_width:
            title_lines[-1] = last_line_with_price
        else:
            title_lines.append(price)

    for line in title_lines:
        draw.text((text_x, y), line, fill=layout.text_color, font=item_font)
        y += text_line_height(item_font, layout.item_line_spacing)

    if item["description"]:
        for line in wrap_text(
            draw, item["description"], description_font, text_width
        ):
            draw.text(
                (text_x, y),
                line,
                fill=layout.description_color,
                font=description_font,
            )
            y += text_line_height(description_font, layout.description_line_spacing)

    return y + layout.item_spacing


def draw_section(
    draw,
    section,
    x,
    y,
    title_font,
    item_font,
    description_font,
    column_width,
    layout,
):
    """Рисует заголовок раздела и его блюда."""

    for line in wrap_text(draw, section["title"], title_font, column_width):
        draw.text((x, y), line, fill=layout.section_color, font=title_font)
        y += text_line_height(title_font, layout.title_spacing)

    for item in section["items"]:
        y = draw_item(
            draw,
            item,
            x,
            y,
            item_font,
            description_font,
            column_width,
            layout,
        )

    return y + layout.section_spacing


def draw_column(
    draw,
    sections,
    x,
    y,
    title_font,
    item_font,
    description_font,
    column_width,
    layout,
):
    """Рисует все разделы одной колонки."""

    for section in sections:
        y = draw_section(
            draw,
            section,
            x,
            y,
            title_font,
            item_font,
            description_font,
            column_width,
            layout,
        )

    return y
