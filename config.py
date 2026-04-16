from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def get_key(name: str, required: bool = True) -> str | None:
    val = os.getenv(name)
    if not val and required:
        raise EnvironmentError(f"Missing required env var: {name}")
    return val


GROQ_API_KEY: str | None = get_key("GROQ_API_KEY", required=True)
GOOGLE_API_KEY: str | None = get_key("GOOGLE_API_KEY", required=False)
OLLAMA_BASE_URL: str = get_key("OLLAMA_BASE_URL", required=False) or "http://localhost:11434"


def check_groq() -> bool:
    try:
        from groq import Groq
        groq_client = Groq(api_key=GROQ_API_KEY)
        groq_client.models.list()
        return True
    except Exception:
        return False
