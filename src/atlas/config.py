"""Configuration intentionally read on demand for test isolation."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def database_path() -> Path:
    return Path(os.getenv("ATLAS_DB_PATH", "./data/atlas.db")).expanduser()


def available_providers() -> dict[str, bool]:
    return {
        "demo": True,
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
    }


DEFAULT_MODELS = {
    "demo": "atlas-demo-v1",
    "openai": "gpt-4.1-mini",
    "anthropic": "claude-sonnet-4-5",
    "gemini": "gemini-2.5-flash",
}
