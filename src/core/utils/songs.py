import secrets

from src.core.config import API_BASE_URL


def generate_track_token() -> str:
    return secrets.token_urlsafe(32)


def generate_track_url(track_token: str) -> str:
    return f"{API_BASE_URL}/track/{track_token}"
