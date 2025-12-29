from aiogram import F, Router
from aiogram.filters.command import CommandObject, CommandStart, Command
from aiogram.types import Message
from src.core.config import SONG_LINK_PATTERN
from src.core.exceptions import (
    AlreadyConnectedError,
    CannotJoinOwnCodeError,
    ConnectionNotFoundError,
    InvalidPairCodeError,
)
from src.core.utils.songs import generate_track_url
from src.modules.connections.service import ConnectionService
from src.modules.songs.service import SongService
from src.modules.users.service import UserService
from src.modules.users.model import UserData
from src.core.logging import logger
from src.modules.songs.model import SendSongData
from src.database.entities.user import User
from src.database.entities.connection import Connection as DBConnection

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message, user_service: UserService):
    if not message.from_user:
        return

    user_data = UserData(
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    logger.info(f"User {user_data.telegram_id} started bot")

    user = await user_service.get_or_create_user(user_data)

    await message.answer(
        f"Hello {user.first_name}! Welcome to Song Pal Bot! 🎵\n\n"
        f"Use /pair to generate a connection code!"
    )


@router.message(Command("pair"), flags={"auth_required": True})
async def pair_handler(
    message: Message, user: User, connection_service: ConnectionService
):
    try:
        connection = await connection_service.get_or_create_pair_code(user.id)

        await message.answer(
            "Send this command to your partner. When they tap it, you'll be linked! 🔗"
        )
        # Send the full command in a separate message
        await message.answer(
            f"`/connect {connection.pair_code}`", parse_mode="Markdown"
        )
    except AlreadyConnectedError as error:
        await message.answer(str(error))


@router.message(Command("connect"), flags={"auth_required": True})
async def connect_handler(
    message: Message,
    command: CommandObject,
    user: User,
    user_service: UserService,
    connection_service: ConnectionService,
):
    pair_code = command.args
    if not pair_code:
        await message.answer("Please provide a code! Usage: `/connect <code>`")
        return

    try:
        connection = await connection_service.join_connection(user.id, pair_code)

        await message.answer(
            "Successfully connected! 🎵\n\n"
            "You can now send Spotify/YouTube links to share music!"
        )

        user1 = await user_service.get_user_by_id(connection.user1_id)

        if user1 and message.bot:
            await message.bot.send_message(
                chat_id=user1.telegram_id,
                text=f"{user.first_name} connected successfully!",
            )

    except (
        ConnectionNotFoundError,
        CannotJoinOwnCodeError,
        InvalidPairCodeError,
    ) as error:
        await message.answer(str(error))


@router.message(Command("disconnect"), flags={"auth_required": True})
async def disconnect_handler(
    message: Message,
    user: User,
    connection_service: ConnectionService,
):
    try:
        await connection_service.leave_connection(user.id)

        await message.answer("Disconnected! 💔\nYou are no longer paired.")

    except ConnectionNotFoundError as e:
        await message.answer(str(e))


@router.message(
    F.text.regexp(SONG_LINK_PATTERN),
    flags={"auth_required": True, "connection_required": True},
)
async def send_song_handler(
    message: Message,
    user: User,
    user_service: UserService,
    connection: DBConnection,
    song_service: SongService,
):
    receiver_id = (
        connection.user2_id if connection.user1_id == user.id else connection.user1_id
    )

    if receiver_id is None:
        await message.answer("Error: Connection corrupted (no receiver found).")
        return

    payload = SendSongData.model_validate(
        {
            "sender_id": user.id,
            "receiver_id": receiver_id,
            "connection_id": connection.id,
            "link": message.text,
        }
    )

    song = await song_service.send_song(payload)

    track_url = generate_track_url(song.track_token)

    receiver_user = await user_service.get_user_by_id(receiver_id)

    if receiver_user and message.bot:
        await message.bot.send_message(
            chat_id=receiver_user.telegram_id,
            text=f"🎵 {user.first_name} sent you a song! Click here to listen: {track_url}",
        )


@router.message(
    Command("status"), flags={"auth_required": True, "connection_required": True}
)
async def status_handler(
    message: Message,
    user: User,
    user_service: UserService,
    connection: DBConnection,
):
    if not connection.user2_id:
        await message.answer(
            "You're not connected! Use /pair to generate a connection code!"
        )
        return

    connected_user_id = (
        connection.user2_id if connection.user1_id == user.id else connection.user1_id
    )

    connected_user = await user_service.get_user_by_id(connected_user_id)

    connected_user_name = (
        connected_user.first_name if connected_user else "Unknown User"
    )

    status_msg = (
        f"🔗 Connected to user: {connected_user_name}\n"
        f"Paired code: {connection.pair_code}\n"
        f"Connected at:"
        f"{connection.connected_at.strftime('%d %B %Y %H:%M') if connection.connected_at else 'N/A'}"
    )
    await message.answer(status_msg)
