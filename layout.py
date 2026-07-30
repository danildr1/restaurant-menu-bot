"""Адаптивные параметры оформления меню."""

from dataclasses import dataclass


IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920

BACKGROUND_COLOR = "#FFFFFF"
TEXT_COLOR = "#222222"
DESCRIPTION_COLOR = "#555555"
SECTION_COLOR = "#3E681D"


@dataclass(frozen=True)
class MenuLayout:
    """Размеры, вычисленные относительно фактического холста."""

    date_y: int
    left_column_x: int
    right_column_x: int
    columns_y: int
    left_column_width: int
    right_column_width: int
    date_font_size: int
    section_font_size: int
    item_font_size: int
    description_font_size: int
    item_spacing: int
    section_spacing: int
    title_spacing: int
    item_line_spacing: int
    description_line_spacing: int
    text_color: str
    description_color: str
    section_color: str


def get_layout(width: int, height: int, content_weight: float = 0) -> MenuLayout:
    """Возвращает раскладку с отступами, зависящими от объёма меню."""

    scale = min(width / IMAGE_WIDTH, height / IMAGE_HEIGHT)

    if content_weight <= 14:
        spacing_scale = 1.6
    elif content_weight <= 25:
        spacing_scale = 1.25
    else:
        spacing_scale = 1

    return MenuLayout(
        date_y=round(height * 0.03125),
        left_column_x=round(width * 0.0556),
        right_column_x=round(width * 0.5556),
        columns_y=round(height * 0.1050),
        left_column_width=round(width * 0.4600),
        right_column_width=round(width * 0.3889),
        date_font_size=round(72 * scale),
        section_font_size=round(49 * scale),
        item_font_size=round(44 * scale),
        description_font_size=round(34 * scale),
        item_spacing=round(18 * scale * spacing_scale),
        section_spacing=round(52 * scale * spacing_scale),
        title_spacing=round(18 * scale),
        item_line_spacing=round(8 * scale),
        description_line_spacing=round(7 * scale),
        text_color=TEXT_COLOR,
        description_color=DESCRIPTION_COLOR,
        section_color=SECTION_COLOR,
    )
