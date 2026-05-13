from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config.settings import settings
from bot.keyboards.user_kb import back_to_menu_keyboard, faq_keyboard, buy_keyboard
from bot.utils.messages import COURSE_INFO, BUY_INFO, FAQ, SUPPORT

router = Router()


@router.callback_query(F.data == "course")
async def course_info(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        COURSE_INFO,
        reply_markup=back_to_menu_keyboard(),
    )


@router.callback_query(F.data == "faq")
async def faq_info(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        FAQ.format(price=settings.COURSE_PRICE),
        reply_markup=faq_keyboard(),
    )


@router.callback_query(F.data == "support")
async def support_info(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        SUPPORT.format(support=settings.SUPPORT_USERNAME),
        reply_markup=back_to_menu_keyboard(),
    )