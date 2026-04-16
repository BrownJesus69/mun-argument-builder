import os
from dotenv import load_dotenv

load_dotenv()


def get_key(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise EnvironmentError(f"Missing required env var: {name}")
    return val


def get_optional_key(name: str) -> str | None:
    return os.getenv(name)


ANTHROPIC_KEY: str = get_key("ANTHROPIC_API_KEY")
GOOGLE_KEY: str | None = get_optional_key("GOOGLE_API_KEY")
