from collections import defaultdict
from typing import Annotated
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from src.database.entities.song import Song

from src.core.enums import ConnectionStatus
from src.core.utils.songs import generate_track_url
from src.database.core import DbSession
from src.database.entities.connection import Connection
from src.database.entities.user import User
from src.telegram_bot.deps import BotDep


class NotificationService:
    def __init__(self, db: AsyncSession, bot: Bot):
        self.db = db
        self.bot = bot

    async def send_unlistened_songs_notification(self):

        stmt = (
            select(Song, User)
            .join(Connection, Song.connection_id == Connection.id)
            .join(User, Song.receiver_id == User.id)
            .where(
                Connection.status == ConnectionStatus.CONNECTED,
                Song.listened_at.is_(None),
            )
        )

        result = await self.db.execute(stmt)

        songs_by_telegram_id = defaultdict[int, list[Song]](list)

        for song, user in result:
            songs_by_telegram_id[user.telegram_id].append(song)

        for telegram_id, songs_list in songs_by_telegram_id.items():
            message_lines = ["🎵⏰ You have unlistened songs!\n"]

            for i, song in enumerate(songs_list, start=1):
                track_url = generate_track_url(song.track_token)
                message_lines.append(f"{i}) {track_url} \n")

            message = "\n".join(message_lines)

            try:
                await self.bot.send_message(chat_id=telegram_id, text=message)
            except TelegramBadRequest as e:
                print(f"Failed to send message to {telegram_id}: {e}")
                continue


async def get_notification_service(db: DbSession, bot: BotDep) -> NotificationService:
    return NotificationService(db, bot)


NotificationServiceDep = Annotated[
    NotificationService, Depends(get_notification_service)
]
