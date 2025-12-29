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
    logger.info("=" * 60)
    logger.info("Starting bot application...")
    logger.info("=" * 60)

    # Validate configuration
    if not TELEGRAM_TOKEN:
        error_msg = "TELEGRAM_TOKEN is not set in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not TELEGRAM_WEBHOOK_SECRET:
        error_msg = "TELEGRAM_WEBHOOK_SECRET is not set in environment variables"
        logger.error(error_msg)
        raise ValueError(error_msg)

    if not WEBHOOK_URL:
        error_msg = "WEBHOOK_URL is not set (API_BASE_URL missing?)"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(
        f"TELEGRAM_TOKEN: {'*' * 20} (length: {len(TELEGRAM_TOKEN) if TELEGRAM_TOKEN else 0})"
    )
    logger.info(
        f"TELEGRAM_WEBHOOK_SECRET: {'*' * 20} (length: {len(TELEGRAM_WEBHOOK_SECRET) if TELEGRAM_WEBHOOK_SECRET else 0})"
    )
    logger.info(f"WEBHOOK_URL: {WEBHOOK_URL}")

    # Initialize bot
    logger.info("Initializing Telegram bot...")
    bot = Bot(token=TELEGRAM_TOKEN)

    try:
        # Get bot info to verify token
        bot_info = await bot.get_me()
        logger.info(
            f"Bot initialized successfully: @{bot_info.username} (ID: {bot_info.id}, Name: {bot_info.first_name})"
        )
    except Exception as e:
        logger.error(f"Failed to get bot info - token may be invalid: {e}")
        raise

    # Set webhook
    logger.info(f"Setting webhook to: {WEBHOOK_URL}")
    try:
        webhook_info = await bot.set_webhook(
            WEBHOOK_URL, secret_token=TELEGRAM_WEBHOOK_SECRET, drop_pending_updates=True
        )
        logger.info(f"Webhook set successfully: {webhook_info}")

        # Verify webhook was set
        webhook_info_check = await bot.get_webhook_info()
        logger.info(
            f"Webhook verification - URL: {webhook_info_check.url}, Pending updates: {webhook_info_check.pending_update_count}"
        )
        if webhook_info_check.url != WEBHOOK_URL:
            logger.warning(
                f"Webhook URL mismatch! Expected: {WEBHOOK_URL}, Got: {webhook_info_check.url}"
            )
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}", exc_info=True)
        raise

    # Setup dispatcher
    logger.info("Setting up dispatcher and middlewares...")
    dispatcher = Dispatcher()

    dispatcher.update.middleware(DatabaseMiddleware())
    logger.debug("DatabaseMiddleware registered")
    dispatcher.update.middleware(ServiceMiddleware())
    logger.debug("ServiceMiddleware registered")
    dispatcher.message.middleware(AuthGuardMiddleware())
    logger.debug("AuthGuardMiddleware registered")
    dispatcher.message.middleware(ConnectionGuardMiddleware())
    logger.debug("ConnectionGuardMiddleware registered")
    dispatcher.include_router(router)
    logger.info("Router included in dispatcher")

    fastapi_app.state.bot = bot
    fastapi_app.state.dispatcher = dispatcher

    logger.info("=" * 60)
    logger.info("Bot application started successfully!")
    logger.info("=" * 60)

    yield

    logger.info("=" * 60)
    logger.info("Shutting down application...")
    logger.info("=" * 60)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Webhook deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}", exc_info=True)
    logger.info("Shutdown complete")


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
    logger.info("=" * 60)
    logger.info("Webhook request received")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request headers: {dict(request.headers)}")

    try:
        bot = request.app.state.bot
        dispatcher = request.app.state.dispatcher

        if not bot:
            logger.error("Bot not found in app state!")
            return {"ok": False, "error": "Bot not initialized"}

        if not dispatcher:
            logger.error("Dispatcher not found in app state!")
            return {"ok": False, "error": "Dispatcher not initialized"}

        # Verify webhook secret
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        logger.info(f"Received secret token: {'*' * 20 if secret_token else 'MISSING'}")

        if secret_token != TELEGRAM_WEBHOOK_SECRET:
            logger.warning(
                f"Invalid webhook secret token! Expected: {'*' * 20}, Got: {'*' * 20 if secret_token else 'MISSING'}"
            )
            return {"ok": False, "error": "Invalid secret token"}

        # Parse request body
        try:
            data = await request.json()
            logger.info(f"Update data received: {data.get('update_id', 'N/A')}")
            logger.debug(f"Full update data: {data}")
        except Exception as e:
            logger.error(f"Failed to parse JSON from request: {e}", exc_info=True)
            return {"ok": False, "error": "Invalid JSON"}

        # Create Update object
        try:
            update = Update(**data)
            logger.info(
                f"Update object created - ID: {update.update_id}, Type: {update.event_type if hasattr(update, 'event_type') else 'unknown'}"
            )
        except Exception as e:
            logger.error(f"Failed to create Update object: {e}", exc_info=True)
            logger.error(f"Data that failed: {data}")
            return {"ok": False, "error": "Invalid update format"}

        # Log update details
        if update.message:
            logger.info(
                f"Message update - From: {update.message.from_user.id if update.message.from_user else 'N/A'}, "
                f"Text: {update.message.text[:50] if update.message.text else 'N/A'}..."
            )
        elif update.callback_query:
            logger.info(
                f"Callback query update - From: {update.callback_query.from_user.id if update.callback_query.from_user else 'N/A'}"
            )
        elif update.inline_query:
            logger.info(
                f"Inline query update - From: {update.inline_query.from_user.id if update.inline_query.from_user else 'N/A'}"
            )
        else:
            logger.info(f"Other update type: {type(update)}")

        # Process update
        logger.info("Feeding update to dispatcher...")
        try:
            # Wrap in try-except to catch any unhandled exceptions
            await dispatcher.feed_update(bot, update)
            logger.info(
                f"Update {update.update_id} processed successfully by dispatcher"
            )
        except Exception as e:
            logger.error(
                f"CRITICAL: Error processing update {update.update_id} in dispatcher: {e}",
                exc_info=True,
            )
            logger.error(f"Exception type: {type(e).__name__}")
            logger.error(f"Exception args: {e.args}")
            # Don't return error to Telegram to avoid retries, but log everything
            return {"ok": True, "error": "Processing failed but acknowledged"}

        logger.info("Webhook request completed successfully")
        logger.info("=" * 60)
        return {"ok": True}

    except Exception as e:
        logger.error(f"Unexpected error in webhook handler: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


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
