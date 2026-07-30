"""Нормализация текста меню перед передачей в парсер."""

import re


SECTION_ALIASES = {
    "САЛАТ": "САЛАТЫ",
    "САЛАТЫ": "САЛАТЫ",
    "СУП": "СУПЫ",
    "СУПЫ": "СУПЫ",
    "ГОРЯЧЕЕ": "ГОРЯЧИЕ БЛЮДА",
    "ГОРЯЧИЕ": "ГОРЯЧИЕ БЛЮДА",
    "ГОРЯЧИЕ БЛЮДА": "ГОРЯЧИЕ БЛЮДА",
    "ГАРНИР": "ГАРНИРЫ",
    "ГАРНИРЫ": "ГАРНИРЫ",
    "НАПИТОК": "НАПИТКИ",
    "НАПИТКИ": "НАПИТКИ",
    "ДЕСЕРТ": "ДЕСЕРТ",
    "ДЕСЕРТЫ": "ДЕСЕРТ",
}

DEFAULT_DATE = "Бизнес-ланч на сегодня"

SPECIAL_CORRECTIONS = {
    "Г реческий": "Греческий",
    "краб.палочки": "крабовые палочки",
    "ветчин": "ветчина",
    "овощам": "овощами",
}

DATE_PATTERN = re.compile(
    r"^\d{1,2}\s+"
    r"(?:января|февраля|марта|апреля|мая|июня|июля|августа|"
    r"сентября|октября|ноября|декабря)$",
    re.IGNORECASE,
)

DATE_PREFIX_PATTERN = re.compile(
    r"^дата\s*:\s*(\d{1,2}\s+"
    r"(?:января|февраля|марта|апреля|мая|июня|июля|августа|"
    r"сентября|октября|ноября|декабря))$",
    re.IGNORECASE,
)

LEADING_LIST_MARKER_PATTERN = re.compile(
    r"^\s*(?:(?:[-—–•●▪◦‣·]+|\d+[.)])\s*)+"
)


def normalize_line(line, corrections):
    """Очищает одну строку меню и применяет безопасные исправления."""

    line = line.replace("\ufeff", "").replace("\u200b", "")
    line = LEADING_LIST_MARKER_PATTERN.sub("", line)
    line = line.replace("«", "").replace("»", "")
    line = re.sub(r"\s+", " ", line).strip()

    for source, replacement in SPECIAL_CORRECTIONS.items():
        pattern = re.compile(rf"\b{re.escape(source)}\b", re.IGNORECASE)
        if pattern.search(line):
            line = pattern.sub(replacement, line)
            corrections.append(f"{source} → {replacement}")

    line = re.sub(r"\s*([,;])\s*", r"\1 ", line)
    line = re.sub(r"\s*\(\s*", " (", line)
    line = re.sub(r"\s*\)", ")", line)
    line = re.sub(
        r"\s*[-—]\s*(\d+)\s*(?:р\.?|руб\.?)\b",
        r" (\1 ₽)",
        line,
        flags=re.IGNORECASE,
    )

    return line


def normalize_menu_text(text):
    """Возвращает текст, понятный parser.py, и список исправлений."""

    corrections = []
    date = None
    lines = []

    for raw_line in text.splitlines():
        line = normalize_line(raw_line, corrections)

        if not line:
            continue

        section_key = re.sub(r"\s*:\s*$", "", line).upper()

        if section_key in SECTION_ALIASES:
            section = SECTION_ALIASES[section_key]
            if line != section:
                corrections.append(f"{line} → {section}")
            lines.append(section)
            continue

        date_prefix_match = DATE_PREFIX_PATTERN.fullmatch(line)
        if date_prefix_match:
            date = date_prefix_match.group(1).lower()
            corrections.append(f"{line} → {date}")
            continue

        if DATE_PATTERN.fullmatch(line):
            date = line.lower()
            continue

        lines.append(line)

    lines.insert(0, date or DEFAULT_DATE)

    return "\n".join(lines), list(dict.fromkeys(corrections))
