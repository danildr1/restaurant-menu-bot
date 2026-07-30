"""
parser.py

Разбирает текст меню и превращает его
в удобную структуру данных.

На вход:

29 июля

САЛАТЫ
Греческий (огурец, сыр...)
Красное море (краб...)

СУПЫ
Лапша куриная

На выход:

{
    "date": "29 июля",
    "sections": [
        {
            "title": "САЛАТЫ",
            "items": [
                {
                    "name": "Греческий",
                    "description": "огурец, сыр..."
                }
            ]
        }
    ]
}
"""

import re


# ============================================================
# Заголовки разделов
# ============================================================

SECTION_TITLES = {
    "САЛАТЫ",
    "СУПЫ",
    "ГОРЯЧИЕ БЛЮДА",
    "ГАРНИРЫ",
    "НАПИТКИ",
    "ДЕСЕРТ",
}

DEFAULT_DATE = "Бизнес-ланч на сегодня"

PRICE_PATTERN = re.compile(r"\s*\((\d+(?:[.,]\d{1,2})?\s*₽)\)\s*$")


# ============================================================
# Разбирает одну строку блюда
# ============================================================

def parse_item(line):
    """
    Было:

    Греческий (огурец, сыр, помидор)

    Стало:

    {
        "name": "Греческий",
        "description": "огурец, сыр, помидор"
    }
    """

    line = line.strip()

    price_match = PRICE_PATTERN.search(line)
    price = ""

    if price_match:
        price = price_match.group(1)
        line = line[:price_match.start()].strip()

    match = re.match(r"^(.*?)\((.*?)\)$", line)

    if match:

        return {
            "name": match.group(1).strip(),
            "description": match.group(2).strip(),
            "price": price,
        }

    return {
        "name": line,
        "description": "",
        "price": price,
    }


# ============================================================
# Главная функция
# ============================================================

def parse_menu(text):

    # Убираем пустые строки

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        raise ValueError("Пустое сообщение")

    # Нормализатор всегда добавляет дату, но эта проверка не даёт потерять
    # первый раздел, если parse_menu вызовут напрямую без нормализации.
    if lines[0].upper() in SECTION_TITLES:
        date = DEFAULT_DATE
        menu_lines = lines
    else:
        date = lines[0]
        menu_lines = lines[1:]

    result = {
        "date": date,
        "sections": []
    }

    current_section = None

    for line in menu_lines:

        upper = line.upper()

        # Если встретили новый раздел

        if upper in SECTION_TITLES:

            current_section = {
                "title": upper,
                "items": []
            }

            result["sections"].append(current_section)

            continue

        # Пока раздела нет —
        # игнорируем строку

        if current_section is None:
            continue

        current_section["items"].append(
            parse_item(line)
        )

    # Пустые разделы иногда возвращаются LLM как заглушки. На изображении
    # им делать нечего, поэтому оставляем только разделы с блюдами.
    result["sections"] = [
        section for section in result["sections"] if section["items"]
    ]

    if not result["sections"]:
        raise ValueError("Не найдены разделы меню")

    return result
