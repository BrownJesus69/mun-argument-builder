"""Shared LLM interface — Groq backend."""

from __future__ import annotations

import json
import os
import re

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.1-8b-instant"


def call_llm(prompt: str, json_mode: bool = False) -> str:
    kwargs: dict = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    r = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        **kwargs,
    )
    return r.choices[0].message.content


def call_llm_json(prompt: str) -> dict:
    raw = call_llm(prompt, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from LLM response: {raw[:200]}")
