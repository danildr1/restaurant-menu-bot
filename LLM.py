import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["OPENROUTER_API_KEY"],
    base_url="https://openrouter.ai/api/v1",
)

SYSTEM_PROMPT = """
Ты редактор меню бизнес-ланча.

Тебе приходит текст после OCR или введенный человеком.

Исправь:
- OCR-ошибки;
- орфографию;
- пунктуацию.

Правила:
- не придумывай блюда;
- не удаляй блюда;
- не меняй порядок строк;
- не объединяй блюда;
- не меняй смысл текста;
- если не уверен — оставь как есть.

Верни только исправленный текст.
Без комментариев.
Без Markdown.
"""

def improve_menu(text: str) -> str:
    response = client.chat.completions.create(
        model="openrouter/free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )

    return response.choices[0].message.content.strip()