from typing import Callable, Any, Dict, Awaitable
from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import TelegramObject, Message

from src.database.core import AsyncSessionLocal
from src.modules.connections.service import ConnectionService
from src.modules.songs.service import SongService
from src.modules.users.service import UserService
from src.core.enums import ConnectionStatus


class DatabaseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ):
        async with AsyncSessionLocal() as session:
            data["db"] = session
            return await handler(event, data)


class ServiceMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ):
        db = data["db"]

        data["user_service"] = UserService(db)
        data["connection_service"] = ConnectionService(db)
        data["song_service"] = SongService(db)

        return await handler(event, data)


class AuthGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ):
        if not isinstance(event, Message):
            return await handler(event, data)

        if not get_flag(data, "auth_required"):
            return await handler(event, data)

        if not event.from_user:
            return await handler(event, data)

        user_service: UserService = data["user_service"]
        user = await user_service.get_user_by_telegram_id(event.from_user.id)

        if not user:
            return await event.answer("Please run /start first!")

        data["user"] = user
        return await handler(event, data)


class ConnectionGuardMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ):
        if not get_flag(data, "connection_required"):
            return await handler(event, data)

        user = data.get("user")
        if not user:
            return await handler(event, data)

        connection_service: ConnectionService = data["connection_service"]
        connection = await connection_service.get_connection(
            user.id, ConnectionStatus.CONNECTED
        )

        if not connection:
            if isinstance(event, Message):
                return await event.answer(
                    "You're not connected! Use /pair to generate a connection code!"
                )
            return None

        data["connection"] = connection
        return await handler(event, data)
