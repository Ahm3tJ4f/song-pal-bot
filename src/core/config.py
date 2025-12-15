import os
from typing import Final
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_TOKEN: Final[str | None] = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_BOT_USERNAME: Final[str | None] = f"@{os.getenv('TELEGRAM_BOT_USERNAME')}"

# Database Configuration
POSTGRES_USER: Final[str | None] = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD: Final[str | None] = os.getenv("POSTGRES_PASSWORD")
POSTGRES_DB: Final[str | None] = os.getenv("POSTGRES_DB")
POSTGRES_HOST: Final[str] = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT: Final[int] = int(os.getenv("POSTGRES_PORT", "5432"))

BASE_DATABASE_URL: Final[str] = (
    f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}"
)

DATABASE_URL: Final[str | None] = (
    f"{BASE_DATABASE_URL}/{POSTGRES_DB}" if POSTGRES_DB else None
)

API_BASE_URL: Final[str | None] = os.getenv("API_BASE_URL")

WEBHOOK_URL: Final[str] = f"{API_BASE_URL}/telegram/webhook"

SONG_LINK_PATTERN: Final[str] = (
    r"https?://(?:open\.spotify\.com|youtu\.be|youtube\.com)[^\s]*"
)
