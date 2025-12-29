from contextlib import asynccontextmanager

from aiogram.types import Update
from aiogram import Bot, Dispatcher
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from src.core.logging import logger
from src.core.config import TELEGRAM_TOKEN, TELEGRAM_WEBHOOK_SECRET, WEBHOOK_URL
from src.database.core import engine
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

    if not TELEGRAM_TOKEN or not TELEGRAM_WEBHOOK_SECRET:
        raise ValueError("TELEGRAM_TOKEN is not set")

    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.set_webhook(WEBHOOK_URL, secret_token=TELEGRAM_WEBHOOK_SECRET)

    dispatcher = Dispatcher()
    dispatcher.update.middleware(DatabaseMiddleware())
    dispatcher.update.middleware(ServiceMiddleware())
    dispatcher.message.middleware(AuthGuardMiddleware())
    dispatcher.message.middleware(ConnectionGuardMiddleware())
    dispatcher.include_router(router)

    fastapi_app.state.bot = bot
    fastapi_app.state.dispatcher = dispatcher

    yield

    logger.info("Shutting down application...")
    await bot.delete_webhook()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health_check():
    """Health check endpoint for Render and monitoring."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    bot = request.app.state.bot
    dispatcher = request.app.state.dispatcher

    data = await request.json()
    update = Update(**data)

    await dispatcher.feed_update(bot, update)

    return {"ok": True}


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
        try:
            await bot.send_message(
                chat_id=sender.telegram_id,
                text=f"🎧 {receiver.first_name} just listened to your song!\n{song.link}",
            )
        except Exception as e:
            logger.error(f"Failed to send listen notification: {e}")

    return RedirectResponse(url=song.link)
