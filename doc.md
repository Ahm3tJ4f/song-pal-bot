## Telegram Song Pal Bot — Spec (v1, Telegram webhook)

### 1) Purpose (short)

- Two people connect, send song links, and track if the receiver opened and marked them listened.
- Automated reminders and weekly shame reports.

### 2) User flow (exclusive pairing: one connection at a time)

1. User A: `/start` or `/pair` → bot generates code (6 chars, e.g., `Q7M2XK`).
2. Bot tells A:
   ```
   Share this with your partner:
   /connect Q7M2XK
   ```
3. User B: `/connect Q7M2XK`.
4. Bot checks:
   - If B already has a confirmed connection → error: "You're already connected. Use /disconnect first."
   - If code is valid and pending → set `status='confirmed'`, clear `pair_code`.
5. Both users are now linked. Only one confirmed connection per user at a time (enforced in service logic).

### 3) Commands

- `/start` – Show welcome message.
- `/pair` – Generate a pair code to share.
- `/connect <code>` – Use a pair code to connect.
- `/disconnect` – Break current connection.
- Send a link (no prefix) – Bot validates URL and forwards to your partner.
- Reply “LISTENED” to the song message – Marks that specific song as listened (via reply-to).

### 4) Sending songs (no command keyword)

1. User pastes a link (bot validates it).
2. Must have a confirmed connection; otherwise: "You're not connected. Use /pair first."
3. Store song: `sender_id`, `receiver_id`, `connection_id?`, `link`, `track_token`, timestamps, clicked/listened flags.
4. Generate tracking URL: `https://<bot-domain>/track/<track_token>`.
5. Forward to receiver:
   ```
   🎵 <SenderName> sent you a song!
   Click here to listen: <tracking_link>
   Reply LISTENED ✅ when you finish (reply to this message)
   ```

### 5) Click tracking

- Endpoint: `GET /track/<track_token>`
- Flow:
  1. Lookup song by `track_token`.
  2. If not clicked → set `clicked=true`, `clicked_at=now()`.
  3. Redirect to original link.

### 6) Mark listened

- User replies “LISTENED” to the song message.
- Bot maps reply-to message → song record; sets `listened=true`, `listened_at=now()`.
- If no matching pending song: "No songs to mark as listened."

### 7) Reminders

- Frequency: every 6 hours (cron / scheduled job).
- Logic: find songs where `listened=false` per user; send reminder including whether `clicked` is true/false.

### 8) Weekly summary / gamification

- Weekly job; aggregate per user: sent, clicked, listened.
- Send playful summary (loser points, streaks optional).

### 9) DB schema (minimal)

```
users
  id (PK)
  telegram_id (BIGINT, UNIQUE, NOT NULL)
  first_name (TEXT, NULL)
  created_at (TIMESTAMPTZ, DEFAULT now())

connections
  id (PK)
  user1_id (FK → users.id, NOT NULL)   -- initiator
  user2_id (FK → users.id, NULL)       -- set on connect
  pair_code (VARCHAR, UNIQUE, NULL)    -- temp code, e.g., "Q7M2XK"
  status (TEXT, NOT NULL, DEFAULT 'pending')  -- pending|confirmed|rejected
  created_at (TIMESTAMPTZ, DEFAULT now())
  confirmed_at (TIMESTAMPTZ, NULL)
  -- Invariants: prevent duplicate pairs (UNIQUE on unordered pair in DB or enforce in service).
  -- Exclusive pairing enforced in service (one confirmed connection per user at a time).

songs
  id (PK)
  sender_id (FK → users.id, NOT NULL)
  receiver_id (FK → users.id, NOT NULL)
  connection_id (FK → connections.id, NULL)  -- optional helper
  link (TEXT, NOT NULL)
  track_token (VARCHAR, UNIQUE, NOT NULL)    -- for /track/<track_token>
  created_at (TIMESTAMPTZ, DEFAULT now())
  clicked (BOOLEAN, DEFAULT false)
  clicked_at (TIMESTAMPTZ, NULL)
  listened (BOOLEAN, DEFAULT false)
  listened_at (TIMESTAMPTZ, NULL)
```

### 10) Notes / requirements

- Telegram Bot API in webhook mode (`/telegram/webhook`).
- FastAPI backend.
- `GET /track/<track_token>` for click → redirect.
- Scheduled jobs for reminders + weekly summary.
- Manual confirmation only; no auto-play detection.
- Pair codes: short (6 chars, reduced alphabet), cleared after confirmation.

### 11) UX copy (short)

```
🎵 Song Pal Bot 🎵
Send songs. Track if they listen. Remind them until they do.
Be annoying. Be the reason they hate you. Weekly shame reports.
/pair to connect
```
