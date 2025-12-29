from typing import Annotated
from fastapi import Depends, Request
from aiogram import Bot


def get_bot(request: Request) -> Bot:
    return request.app.state.bot


BotDep = Annotated[Bot, Depends(get_bot)]
