from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from bot.config.settings import settings


async def is_subscribed(bot: Bot, user_id: int) -> bool:
    """
    Проверяет, является ли пользователь участником основного канала.
    Возвращает True если подписан или если проверить не получилось
    (чтобы не блокировать покупку при ошибках API).
    """
    try:
        member = await bot.get_chat_member(settings.CHANNEL_ID, user_id)
        result = member.status not in ("left", "kicked")
        logger.debug(
            "is_subscribed: user_id={} status={} result={} ",
            user_id,
            member.status,
            result,
        )
        return result
    except TelegramBadRequest as exc:
        logger.debug(
            "is_subscribed: user_id={} TelegramBadRequest={} channel_id={} ",
            user_id,
            exc,
            settings.CHANNEL_ID,
        )
        # Бот не добавлен в канал или канал не найден — пропускаем проверку
        return True


async def check_channel_membership(bot: Bot, user_id: int) -> bool | None:
    """
    Проверяет, является ли пользователь участником основного канала.
    Возвращает True/False, или None при ошибке API.
    """
    try:
        member = await bot.get_chat_member(settings.CHANNEL_ID, user_id)
        result = member.status not in ("left", "kicked")
        logger.debug(
            "check_channel_membership: user_id={} status={} result={} ",
            user_id,
            member.status,
            result,
        )
        return result
    except TelegramBadRequest as exc:
        message = str(exc).lower()
        logger.debug(
            "check_channel_membership: user_id={} TelegramBadRequest={} channel_id={} ",
            user_id,
            exc,
            settings.CHANNEL_ID,
        )
        if "chat not found" in message or "bot was kicked" in message:
            logger.warning(
                "check_channel_membership: channel access issue for channel_id={} — treating as not member",
                settings.CHANNEL_ID,
            )
            return False
        return None