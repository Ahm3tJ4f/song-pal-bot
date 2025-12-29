# Song Pal Bot

Song Pal Bot is a Telegram bot designed to help two people share music and hold each other accountable for listening to it. It facilitates a dedicated connection between two users, tracks song clicks, and manages "listened" statuses.

## 🚀 Features

- **Exclusive Pairing**: Users can generate a unique code to pair with exactly one partner.
- **Song Sharing**: Automatically detects Spotify and YouTube links sent in chat and forwards them to the connected partner.
- **Click Tracking**: Songs are sent with a unique tracking URL. The system records when the partner clicks the link.
- **Listen Confirmation**: Users can reply "LISTENED" to a song message to mark it as complete.
- **Async Architecture**: Built on a fully asynchronous Python stack for performance and scalability.
- **Dockerized**: Ready for deployment with Docker Compose.

## 🏗 Architecture & Design Decisions

The project follows a modular, service-oriented architecture to keep concerns separated and the codebase maintainable.

### Tech Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) serves as the web server. It handles the Telegram Webhook and the HTTP redirect endpoints for link tracking.
- **Telegram Library**: [aiogram 3.x](https://docs.aiogram.dev/) is used for all bot logic. It's fully async and provides a powerful routing system.
- **Database**: [PostgreSQL](https://www.postgresql.org/) is the primary data store.
- **ORM**: [SQLAlchemy (Async)](https://www.sqlalchemy.org/) handles database interactions.
- **Migrations**: [Alembic](https://alembic.sqlalchemy.org/) manages database schema changes.

### Key Architectural Patterns

1.  **Service Layer Pattern**: Business logic is encapsulated in "services" (e.g., `UserService`, `ConnectionService`, `SongService`) located in `src/modules/`. Handlers rely on these services rather than accessing the database directly.
2.  **Dependency Injection**:
    - **FastAPI**: Uses `Depends` for injecting services into HTTP endpoints.
    - **aiogram**: Custom middlewares (`DatabaseMiddleware`, `ServiceMiddleware`) inject database sessions and initialized services into every Telegram update handler. This ensures every message handler has ready-to-use services.
3.  **Webhook over Polling**: The bot is designed for production use with Webhooks. This is more resource-efficient than long-polling and integrates seamlessly with FastAPI.
4.  **Tracking Wrapper**: When User A sends a link, the bot saves it and generates a unique token. User B receives a link to `https://api.domain.com/track/<token>`. Clicking this endpoint logs the timestamp and immediately redirects to the original music URL.

## 📂 Project Structure

```
song-pal-bot/
├── alembic/                # Database migrations
├── src/
│   ├── core/               # Configuration, logging, utils, exceptions
│   ├── database/           # DB setup and models (entities)
│   ├── modules/            # Domain logic (User, Connection, Song services)
│   ├── telegram_bot/       # Handlers, middlewares, and router setup
│   └── main.py             # FastAPI entrypoint
├── docker-compose.yml      # Orchestration
├── requirements.txt        # Python dependencies
└── doc.md                  # Initial spec/documentation
```

## 🛠 How to Run

### Prerequisites

- **Docker** & **Docker Compose**
- A **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- A public HTTPS URL (e.g., using `ngrok` for local dev) to set as the webhook.

### Environment Variables

Create a `.env` file in the root directory (copy from below):

```ini
# Database
POSTGRES_USER=songpal
POSTGRES_PASSWORD=secret
POSTGRES_DB=songpal
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Telegram
TELEGRAM_TOKEN=your_bot_token_here
TELEGRAM_BOT_USERNAME=your_bot_username  # e.g. SongPalBot (no @)

# API (Webhook & Tracking)
API_BASE_URL=https://your-public-url.com
API_PORT=8000
```

### Running with Docker (Recommended)

1.  **Start the services**:

    ```bash
    docker compose up --build
    ```

    This will start Postgres and the FastAPI app. The app automatically applies database migrations on startup.

2.  **Set the Webhook**:
    You need to tell Telegram where to send updates. Run this `curl` command (replace values):

    ```bash
    curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<YOUR_API_BASE_URL>/telegram/webhook"
    ```

3.  **Verify**:
    Visit `http://localhost:8000/health` or `<YOUR_API_BASE_URL>/health`. You should see `{"status": "healthy", "database": "connected"}`.

### Local Development (No Docker)

If you prefer running Python locally:

1.  Start a Postgres instance (or use the one from docker-compose).
2.  Create a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
3.  Run migrations:
    ```bash
    alembic upgrade head
    ```
4.  Start the server:
    ```bash
    uvicorn src.main:app --reload
    ```
    _Note: Ensure your `.env` points `POSTGRES_HOST` to `localhost`._

## 📱 User Flow

1.  **Start**: Send `/start` to register.
2.  **Pair**:
    - User A runs `/pair` to get a code (e.g., `AB12CD`).
    - User A shares code with User B.
    - User B runs `/connect AB12CD`.
    - Both are now notified of the connection.
3.  **Share**:
    - User A sends a Spotify link.
    - User B receives a "User A sent you a song!" message with a tracking link.
4.  **Listen**:
    - User B clicks the link -> Bot records "clicked".
    - User B listens and replies "LISTENED" to the bot's message -> Bot records "listened".
