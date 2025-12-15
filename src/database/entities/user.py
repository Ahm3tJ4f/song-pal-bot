from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.functions import now

from src.database.core import Base


# webhook /start command payload
# {
#   "update_id": 61408046,
#   "message": {
#     "message_id": 24,
#     "from": {
#       "id": 987911659,
#       "is_bot": false,
#       "first_name": "Əhməd",
#       "last_name": "Cəfərov",
#       "username": "ahm3tj4f",
#       "language_code": "en"
#     },
#     "chat": {
#       "id": 987911659,
#       "first_name": "Əhməd",
#       "last_name": "Cəfərov",
#       "username": "ahm3tj4f",
#       "type": "private"
#     },
#     "date": 1765025123,
#     "text": "/start",
#     "entities": [
#       {
#         "offset": 0,
#         "length": 6,
#         "type": "bot_command"
#       }
#     ]
#   }
# } |


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=now(), nullable=False
    )
