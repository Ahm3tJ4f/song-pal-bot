from typing import Optional

from pydantic import BaseModel


class UserData(BaseModel):
    telegram_id: int
    first_name: str
    last_name: Optional[str] = None
