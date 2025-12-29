import os
from typing import Final
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Configuration
TELEGRAM_TOKEN: Final[str | None] = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_BOT_USERNAME: Final[str | None] = f"@{os.getenv('TELEGRAM_BOT_USERNAME')}"

DATABASE_URL: Final[str | None] = os.getenv("DATABASE_URL")


API_BASE_URL: Final[str | None] = os.getenv("API_BASE_URL")

WEBHOOK_URL: Final[str] = f"{API_BASE_URL}/telegram/webhook"

SONG_LINK_PATTERN: Final[str] = (
    r"https?://(?:open\.spotify\.com|youtu\.be|youtube\.com)[^\s]*"
)

TELEGRAM_WEBHOOK_SECRET: Final[str | None] = os.getenv("TELEGRAM_WEBHOOK_SECRET")
