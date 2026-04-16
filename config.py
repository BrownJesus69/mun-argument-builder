from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")

ANTHROPIC_KEY: str | None = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_KEY: str | None = os.getenv("GOOGLE_API_KEY")


def check_ollama() -> bool:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except:  # noqa: E722
        return False
