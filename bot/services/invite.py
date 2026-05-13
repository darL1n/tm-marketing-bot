from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from bot.config.settings import settings


async def generate_invite_link(bot: Bot) -> str:
    try:
        invite = await bot.create_chat_invite_link(settings.CHANNEL_ID, member_limit=1)
        return invite.invite_link
    except TelegramBadRequest:
        return f"https://t.me/c/{settings.CHANNEL_ID}" if isinstance(settings.CHANNEL_ID, int) else str(settings.CHANNEL_ID)