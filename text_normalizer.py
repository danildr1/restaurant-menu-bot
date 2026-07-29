"""Нормализация текста меню перед подтверждением пользователем."""

from functools import lru_cache
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

SPECIAL_CORRECTIONS = {
    "Г реческий": "Греческий",
    "краб.палочки": "крабовые палочки",
    "ветчин": "ветчина",
    "овощам": "овощами",
}

PROTECTED_WORDS = {
    "габриэль",
    "чахохбили",
    "цукини",
    "зразы",
    "минтай",
    "пекинка",
    "ветчина",
    "ветчиной",
    "сыр",
    "сыром",
    "овощами",
    "помидор",
    "помидоры",
    "огурцы",
    "перец",
    "соус",
    "майонез",
    "яйцо",
    "рис",
    "макароны",
    "картофель",
    "компот",
    "сухофруктов",
}

DATE_PATTERN = re.compile(
    r"^\d{1,2}\s+"
    r"(?:января|февраля|марта|апреля|мая|июня|июля|августа|"
    r"сентября|октября|ноября|декабря)$",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def get_spell_checker():
    """Создаёт русскоязычный словарь для осторожной проверки опечаток."""

    from spellchecker import SpellChecker

    return SpellChecker(language="ru", distance=1)


def restore_case(source, replacement):
    """Сохраняет регистр слова после исправления."""

    if source.isupper():
        return replacement.upper()
    if source.istitle():
        return replacement.capitalize()
    return replacement


def correct_spelling(line, corrections):
    """Находит сомнительные слова, не изменяя их автоматически."""

    checker = get_spell_checker()

    def replace_word(match):
        word = match.group(0)
        normalized = word.lower()

        if word[0].isupper() or normalized in PROTECTED_WORDS or len(word) < 4:
            return word

        if normalized not in checker.unknown([normalized]):
            return word

        replacement = checker.correction(normalized)

        if replacement and replacement != normalized:
            suggestion = restore_case(word, replacement)
            corrections.append(
                f"Проверь орфографию: {word} (возможный вариант: {suggestion})"
            )

        return word

    return re.sub(r"[А-Яа-яЁё]+", replace_word, line)


def normalize_line(line, corrections):
    """Очищает одну строку меню и применяет безопасные исправления."""

    line = line.replace("\ufeff", "").replace("\u200b", "")
    line = re.sub(r"^[\s•●▪◦‣·]+", "", line)
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

    return correct_spelling(line, corrections)


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

        if DATE_PATTERN.fullmatch(line):
            date = line.lower()
            continue

        lines.append(line)

    if date:
        lines.insert(0, date)

    return "\n".join(lines), list(dict.fromkeys(corrections))
