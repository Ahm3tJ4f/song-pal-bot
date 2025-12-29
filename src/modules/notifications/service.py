from typing import Annotated
from aiogram import Bot
from fastapi import Depends
from src.modules.songs.service import SongService, SongServiceDep
from src.modules.users.service import UserService, UserServiceDep


class NotificationService:
    def __init__(self, song_service: SongService, user_service: UserService, bot: Bot):
        self.song_service = song_service
        self.user_service = user_service
        self.bot = bot

    async def send_unlistened_songs_notification(self):
        unlistened_songs = await self.song_service.get_unlistened_songs()


async def get_notification_service(
    song_service: SongServiceDep,
    user_service: UserServiceDep,
    bot: Bot,
) -> NotificationService:
    return NotificationService(song_service, user_service, bot)


NotificationServiceDep = Annotated[
    NotificationService, Depends(get_notification_service)
]
