from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from bot.config.settings import settings


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """
    Проверяет, является ли пользователь участником основного канала.
    Возвращает True если подписан или если проверить не получилось
    (чтобы не блокировать покупку при ошибках API).
    """
    try:
        member = await bot.get_chat_member(settings.CHANNEL_ID, user_id)
        # left / kicked → не подписан
        return member.status not in ("left", "kicked")
    except TelegramBadRequest:
        # Бот не добавлен в канал или канал не найден — пропускаем проверку
        return True