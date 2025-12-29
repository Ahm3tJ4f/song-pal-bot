from contextlib import asynccontextmanager

from aiogram.types import Update
from aiogram import Bot, Dispatcher
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from src.core.config import TELEGRAM_TOKEN, TELEGRAM_WEBHOOK_SECRET, WEBHOOK_URL
from src.modules.songs.service import SongServiceDep
from src.modules.users.service import UserServiceDep
from src.telegram_bot.handlers import router
from src.telegram_bot.middlewares import (
    DatabaseMiddleware,
    ServiceMiddleware,
    AuthGuardMiddleware,
    ConnectionGuardMiddleware,
)


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    # if not TELEGRAM_TOKEN:
    #     raise ValueError("TELEGRAM_TOKEN is not set in environment variables")
    # if not TELEGRAM_WEBHOOK_SECRET:
    #     raise ValueError("TELEGRAM_WEBHOOK_SECRET is not set in environment variables")
    # if not WEBHOOK_URL:
    #     raise ValueError("WEBHOOK_URL is not set (API_BASE_URL missing?)")

    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.get_me()
    await bot.set_webhook(
        WEBHOOK_URL, secret_token=TELEGRAM_WEBHOOK_SECRET, drop_pending_updates=True
    )

    dispatcher = Dispatcher()
    dispatcher.update.middleware(DatabaseMiddleware())
    dispatcher.update.middleware(ServiceMiddleware())
    dispatcher.message.middleware(AuthGuardMiddleware())
    dispatcher.message.middleware(ConnectionGuardMiddleware())
    dispatcher.include_router(router)

    fastapi_app.state.bot = bot
    fastapi_app.state.dispatcher = dispatcher

    yield

    await bot.delete_webhook(drop_pending_updates=True)


app = FastAPI(lifespan=lifespan)


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    bot = request.app.state.bot
    dispatcher = request.app.state.dispatcher
    data = await request.json()
    update = Update(**data)
    await dispatcher.feed_update(bot, update)

    return {"ok": True}


@app.get("/")
async def health_check():
    return {"status": "ok", "service": "SongPal Bot"}


@app.get("/track/{track_token}")
async def track_song(
    request: Request,
    track_token: str,
    song_service: SongServiceDep,
    user_service: UserServiceDep,
):
    song = await song_service.click_song(track_token)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    # Notify the sender
    sender = await user_service.get_user_by_id(song.sender_id)
    receiver = await user_service.get_user_by_id(song.receiver_id)

    if sender and receiver:
        bot: Bot = request.app.state.bot
        await bot.send_message(
            chat_id=sender.telegram_id,
            text=f"🎧 {receiver.first_name} just listened to your song!\n{song.link}",
        )

    return RedirectResponse(url=song.link)
