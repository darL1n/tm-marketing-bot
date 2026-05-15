from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
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
        bot = data.get("bot")

        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        if user_id is None:
            if isinstance(event, Message):
                await event.answer(NO_ACCESS)
            elif isinstance(event, CallbackQuery):
                await event.answer(NO_ACCESS, show_alert=True)
            return

        # Check if user is a member of the admin group
        try:
            member = await bot.get_chat_member(settings.ADMIN_GROUP_ID, user_id)
            if member.status not in ("administrator", "creator", "member"):
                if isinstance(event, Message):
                    await event.answer(NO_ACCESS)
                elif isinstance(event, CallbackQuery):
                    await event.answer(NO_ACCESS, show_alert=True)
                return
        except TelegramBadRequest:
            # If can't check, deny access
            if isinstance(event, Message):
                await event.answer(NO_ACCESS)
            elif isinstance(event, CallbackQuery):
                await event.answer(NO_ACCESS, show_alert=True)
            return

        return await handler(event, data)