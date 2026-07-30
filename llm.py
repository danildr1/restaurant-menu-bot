import os
import base64
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

MENU_SECTION_MARKERS = (
    "салаты",
    "супы",
    "горячие блюда",
    "гарниры",
    "напитки",
    "десерт",
)

VISION_MODEL = os.getenv(
    "VISION_MODEL",
    os.getenv("OCR_MODEL", "openai/gpt-4o-mini"),
)

SYSTEM_PROMPT = """
Ты — помощник, который преобразует OCR-текст меню ресторана в структурированный вид.

Твоя задача:

1. Исправить ошибки OCR.
2. Исправить орфографию.
3. Исправить переносы строк.
4. Удалить случайные символы, текст на других языках и OCR-мусор.
5. Не придумывать блюда.
6. Не менять порядок блюд.
7. Не удалять блюда, если их можно распознать.
8. Если дата присутствует, извлеки только число и месяц.
   Примеры:
   30 июля
   5 августа
   12 сентября

Верни результат СТРОГО в таком формате:

Дата: <число месяц>

Салаты:
- ...

Супы:
- ...

Горячие блюда:
- ...

Гарниры:
- ...

Напитки:
- ...

Десерт:
- ... (150 ₽)

Не добавляй никаких комментариев.
Верни только этот текст.
Первая непустая строка результата всегда должна быть датой. Если даты нет
в исходном тексте, первой строкой напиши строго: Бизнес-ланч на сегодня.
Добавляй раздел только если в исходном тексте для него есть хотя бы одно блюдо.
Никогда не добавляй пустые разделы.
Если есть десерт, обязательно сохрани его в разделе «Десерт» и не теряй цену.
Цену блюда возвращай в формате: Название (150 ₽).
В раздел «Напитки» добавляй только напитки. Блины, выпечка, сладости и другие
не напитки не должны попадать в этот раздел; размещай их в «Десерт».
Заголовки в OCR могут быть пустыми, перепутанными или стоять не рядом с блюдами.
В таком случае классифицируй блюда по смыслу, а не по ближайшему заголовку:
супы помещай в «Супы», а мясные, рыбные и овощные вторые блюда — в «Горячие блюда».
Весь текст результата должен быть только на русском языке и кириллицей.
Не используй латиницу, диакритические символы и иностранное написание названий.
Иностранные названия блюд передавай русской транслитерацией: Niçoise → Нисуаз.
Всегда используй именно эти названия разделов:
Дата
Если дата отсутствует, напиши "Бизнес-ланч на сегодня"
Салаты
Супы
Горячие блюда
Гарниры
Напитки
Десерт
Исправляй все орфографические ошибки в русском языке, если уверен в исправлении.
"""

def is_menu_response(text: str) -> bool:
    """Проверяет, что провайдер вернул меню, а не служебное сообщение."""

    normalized = text.lower()

    if "user safety:" in normalized:
        return False

    return any(marker in normalized for marker in MENU_SECTION_MARKERS)


def improve_menu(text: str) -> str:
    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )

    result = response.choices[0].message.content.strip()

    if not is_menu_response(result):
        return text

    return result


def improve_menu_from_image(image_bytes: bytes) -> str:
    """Распознаёт фото и сразу возвращает структурированное меню."""

    image_base64 = base64.b64encode(image_bytes).decode("ascii")
    response = client.chat.completions.create(
        model=VISION_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Распознай фотографию и верни готовое меню.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        },
                    }
                ],
            },
        ],
    )

    result = response.choices[0].message.content

    if not result or not is_menu_response(result):
        raise ValueError("Модель не смогла распознать меню на фотографии")

    return result.strip()
