from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config.settings import settings
from bot.utils.messages import NO_ACCESS


class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id: int | None = None

        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id is None or user_id not in settings.ADMIN_IDS:
            if isinstance(event, Message):
                await event.answer(NO_ACCESS)
            elif isinstance(event, CallbackQuery):
                await event.answer(NO_ACCESS, show_alert=True)
            return

        return await handler(event, data)