from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from loguru import logger

from bot.config.settings import settings


async def generate_invite_link(bot: Bot) -> str | None:
    channel_id = settings.CHANNEL_ID
    try:
        invite = await bot.create_chat_invite_link(
            channel_id,
            member_limit=1,
            expire_date=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24),
        )
        logger.debug(
            "Invite created: chat_id={chat_id}, invite_link={invite}",
            chat_id=channel_id,
            invite=invite.invite_link,
        )
        return invite.invite_link
    except TelegramBadRequest as exc:
        logger.warning(
            "Failed to create invite link for chat_id={chat_id}: {exc}",
            chat_id=channel_id,
            exc=exc,
        )
        return None
    except Exception as exc:
        logger.exception(
            "Unexpected error while creating invite link for chat_id={chat_id}",
            channel_id,
        )
        return None


async def revoke_invite_link(bot: Bot, invite_link: str) -> bool:
    channel_id = settings.CHANNEL_ID
    try:
        await bot.revoke_chat_invite_link(channel_id, invite_link=invite_link)
        logger.debug(
            "Invite revoked: chat_id={chat_id}, invite_link={invite}",
            chat_id=channel_id,
            invite=invite_link,
        )
        return True
    except TelegramBadRequest as exc:
        logger.warning(
            "Failed to revoke invite link for chat_id={chat_id}, invite_link={invite}: {exc}",
            chat_id=channel_id,
            invite=invite_link,
            exc=exc,
        )
        return False
    except Exception as exc:
        logger.exception(
            "Unexpected error while revoking invite link for chat_id={chat_id}",
            channel_id,
        )
        return False