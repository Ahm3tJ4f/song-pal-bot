from contextlib import asynccontextmanager

from aiogram.types import Update
from aiogram import Bot, Dispatcher
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from src.core.logging import logger
from src.core.config import TELEGRAM_TOKEN, WEBHOOK_URL
from src.modules.songs.service import SongServiceDep
from src.telegram_bot.handlers import router
from src.telegram_bot.middlewares import DatabaseMiddleware, ServiceMiddleware


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    logger.info("Starting up application...")

    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.set_webhook(WEBHOOK_URL)

    dispatcher = Dispatcher()
    dispatcher.update.middleware(DatabaseMiddleware())
    dispatcher.update.middleware(ServiceMiddleware())
    dispatcher.include_router(router)

    fastapi_app.state.bot = bot
    fastapi_app.state.dispatcher = dispatcher

    yield

    logger.info("Shutting down application...")
    await bot.delete_webhook()


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return {"message": "Song Pal Bot API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
    }


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    bot = request.app.state.bot
    dispatcher = request.app.state.dispatcher

    data = await request.json()
    update = Update(**data)

    await dispatcher.feed_update(bot, update)

    return {"ok": True}


@app.get("/track/{track_token}")
async def track_song(track_token: str, song_service: SongServiceDep):
    song = await song_service.click_song(track_token)

    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    return RedirectResponse(url=song.link)
