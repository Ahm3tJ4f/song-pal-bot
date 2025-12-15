import re

from pydantic import BaseModel, HttpUrl, field_validator

from src.core.config import SONG_LINK_PATTERN


class SendSongData(BaseModel):
    sender_id: int
    receiver_id: int
    connection_id: int
    link: HttpUrl

    @field_validator("link")
    @classmethod
    def validate_music_link(cls, v: HttpUrl) -> HttpUrl:
        url_str = str(v)
        if not re.search(SONG_LINK_PATTERN, url_str):
            raise ValueError("Link must be from Spotify or YouTube")
        return v
