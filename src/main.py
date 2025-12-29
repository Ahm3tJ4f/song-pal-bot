import secrets
from contextlib import asynccontextmanager

from aiogram.types import Update
from aiogram import Bot, Dispatcher
from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import RedirectResponse
from src.core.config import (
    CRON_JOB_SECRET,
    TELEGRAM_TOKEN,
    TELEGRAM_WEBHOOK_SECRET,
    WEBHOOK_URL,
)
from src.modules.notifications.service import NotificationServiceDep
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
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN is not set in environment variables")

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

    await bot.session.close()


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

    sender = await user_service.get_user_by_id(song.sender_id)
    receiver = await user_service.get_user_by_id(song.receiver_id)

    if sender and receiver:
        bot: Bot = request.app.state.bot
        await bot.send_message(
            chat_id=sender.telegram_id,
            text=f"🎧 {receiver.first_name} just listened to your song!\n{song.link}",
        )

    return RedirectResponse(url=song.link)


@app.post("/cron/song-reminders")
async def cron_send_reminders(
    notification_service: NotificationServiceDep,
    x_api_secret: str = Header(..., alias="X-API-Secret"),
):
    if not CRON_JOB_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error",
        )

    if not secrets.compare_digest(x_api_secret, CRON_JOB_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized")

    await notification_service.send_unlistened_songs_notification()
    return {"status": "success", "message": "Reminder notifications sent"}
