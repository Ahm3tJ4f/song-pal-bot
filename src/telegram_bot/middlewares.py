from typing import Callable, Any, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from src.database.core import AsyncSessionLocal
from src.modules.connections.service import ConnectionService
from src.modules.songs.service import SongService
from src.modules.users.service import UserService


class DatabaseMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Awaitable[Any]:
        async with AsyncSessionLocal() as session:
            data["db"] = session
            return await handler(event, data)


class ServiceMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Awaitable[Any]:
        db = data["db"]

        data["user_service"] = UserService(db)
        data["connection_service"] = ConnectionService(db)
        data["song_service"] = SongService(db)

        return await handler(event, data)
