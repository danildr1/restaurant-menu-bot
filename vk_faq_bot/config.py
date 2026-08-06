"""Настройки VK FAQ-бота."""

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
load_dotenv()


def required_env(name: str) -> str:
    """Возвращает обязательную переменную окружения или понятную ошибку."""

    value = os.getenv(name)
    if not value:
        raise ValueError(f"Не задана обязательная переменная окружения {name}")
    return value


VK_GROUP_TOKEN = required_env("VK_GROUP_TOKEN")
VK_GROUP_ID = int(required_env("VK_GROUP_ID"))
LLM_API_KEY = required_env("LLM_API_KEY")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
TEXT_MODEL = os.getenv("TEXT_MODEL", "gpt-4o-mini")
KNOWLEDGE_BASE_PATH = Path(
    os.getenv("KNOWLEDGE_BASE_PATH", BASE_DIR / "knowledge_base.md")
)
