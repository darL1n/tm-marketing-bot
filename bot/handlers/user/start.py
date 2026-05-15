from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from loguru import logger
from sqlalchemy import select

from bot.config.settings import settings
from bot.keyboards.user_kb import active_main_menu_keyboard, main_menu_keyboard
from bot.models.user import User
from bot.services.subscription import check_channel_membership
from bot.utils.messages import ALREADY_ACTIVE, WELCOME

router = Router()


async def _upsert_user(session, tg_user) -> User:
    """Создаёт пользователя если его ещё нет."""
    result = await session.execute(select(User).where(User.tg_id == tg_user.id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            tg_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            is_active=False,
        )
        session.add(user)
        await session.commit()
    return user


async def _render_start_message(tg_user, bot, session) -> tuple[str, object]:
    user = await _upsert_user(session, tg_user)
    logger.debug(
        "start: user_id={} is_active={} user_exists={} ",
        tg_user.id,
        user.is_active,
        user.id is not None,
    )

    membership = await check_channel_membership(bot, tg_user.id)
    logger.debug(
        "start: user_id={} membership={} ",
        tg_user.id,
        membership,
    )

    if membership is False:
        if user.is_active:
            user.is_active = False
            await session.commit()
            logger.debug("start: reset is_active for user_id={} after channel leave", tg_user.id)
        return WELCOME, main_menu_keyboard()

    if membership is True:
        if not user.is_active:
            user.is_active = True
            await session.commit()
            logger.debug("start: set is_active for user_id={} after channel membership confirmed", tg_user.id)
        return ALREADY_ACTIVE, active_main_menu_keyboard()

    if user.is_active:
        logger.debug(
            "start: membership unknown for user_id={} but user.is_active is True, keeping active status",
            tg_user.id,
        )
        return ALREADY_ACTIVE, active_main_menu_keyboard()

    return WELCOME, main_menu_keyboard()


@router.message(Command("start"))
async def cmd_start(message: Message, session):
    text, keyboard = await _render_start_message(message.from_user, message.bot, session)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery, session):
    text, keyboard = await _render_start_message(callback.from_user, callback.bot, session)
    await callback.answer()
    await callback.message.edit_text(text, reply_markup=keyboard)
