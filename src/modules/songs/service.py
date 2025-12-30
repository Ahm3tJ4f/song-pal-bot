from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select

from src.core.utils.songs import generate_track_token
from src.database import Song
from src.database.core import DbSession
from src.modules.songs.model import SendSongData


class SongService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_song(self, payload: SendSongData):

        track_token = generate_track_token()

        new_song = Song(
            sender_id=payload.sender_id,
            receiver_id=payload.receiver_id,
            connection_id=payload.connection_id,
            link=str(payload.link),
            track_token=track_token,
        )

        self.db.add(new_song)
        await self.db.commit()
        return new_song

    async def click_song(
        self, track_token: str, mark_as_listened: bool = True
    ) -> Optional[Song]:
        stmt = select(Song).where(Song.track_token == track_token)
        result = await self.db.execute(stmt)
        song = result.scalar_one_or_none()

        if not song:
            return None

        now = datetime.now(timezone.utc)

        # Update clicked_at if not set
        if not song.clicked_at:
            song.clicked_at = now

        # Update listened_at only if mark_as_listened is True (skip for preview bots)
        if mark_as_listened and not song.listened_at:
            song.listened_at = now

        await self.db.commit()
        return song

    # async def listen_song(self, track_token: str) -> Optional[Song]:
    #     # Kept for backward compatibility or manual marking if needed,
    #     # but usage in handlers will be removed.
    #     stmt = select(Song).where(Song.track_token == track_token)
    #     result = await self.db.execute(stmt)
    #     song = result.scalar_one_or_none()

    #     if not song:
    #         return None

    #     if song.listened_at:
    #         return song

    #     song.listened_at = datetime.now(timezone.utc)

    #     await self.db.commit()
    #     return song

    # async def get_unlistened_songs(self) -> list[Song]:
    #     stmt = select(Song).where(Song.listened_at.is_(None))

    #     result = await self.db.execute(stmt)

    #     return list[Song](result.scalars().all())


async def get_song_service(db: DbSession) -> SongService:
    return SongService(db)


SongServiceDep = Annotated[SongService, Depends(get_song_service)]
