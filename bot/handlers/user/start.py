from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from bot.keyboards.user_kb import main_menu_keyboard
from bot.models.user import User
from bot.utils.messages import WELCOME

router = Router()


async def _upsert_user(session, tg_user) -> None:
    """Создаёт пользователя если его ещё нет."""
    result = await session.execute(select(User).where(User.tg_id == tg_user.id))
    user = result.scalar_one_or_none()
    if not user:
        session.add(User(
            tg_id=tg_user.id,
            username=tg_user.username,
            full_name=tg_user.full_name,
            is_active=False,
        ))
        await session.commit()


@router.message(Command("start"))
async def cmd_start(message: Message, session):
    await _upsert_user(session, message.from_user)
    await message.answer(WELCOME, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery, session):
    await _upsert_user(session, callback.from_user)
    await callback.answer()
    await callback.message.edit_text(WELCOME, reply_markup=main_menu_keyboard())