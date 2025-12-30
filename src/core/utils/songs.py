import secrets

from fastapi import Request
from src.core.config import API_BASE_URL


def generate_track_token() -> str:
    return secrets.token_urlsafe(32)


def generate_track_url(track_token: str) -> str:
    return f"{API_BASE_URL}/track/{track_token}"


def is_telegram_preview_bot(request: Request) -> bool:

    user_agent = request.headers.get("user-agent", "")

    if user_agent and "TelegramBot" in user_agent:
        return True

    if request.client:
        client_host = request.client.host
        if client_host and client_host.startswith("149.154."):
            return True

    return False
