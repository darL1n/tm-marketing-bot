from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.settings import settings
from bot.keyboards.admin_kb import review_keyboard
from bot.models.payment import Payment, PaymentStatus
from bot.models.user import User
from bot.services.invite import generate_invite_link
from bot.utils.messages import PAYMENT_APPROVED, PAYMENT_REJECTED

router = Router()


@router.callback_query(F.data.startswith("review:"))
async def review_payment(callback: CallbackQuery, session: AsyncSession):
    await callback.answer()
    _, action, payment_id_str = callback.data.split(":", 2)
    payment_id = int(payment_id_str)

    result = await session.execute(select(Payment).where(Payment.id == payment_id))
    payment = result.scalar_one_or_none()

    if not payment:
        await callback.message.answer("⚠️ Платёж не найден.")
        return

    if payment.status != PaymentStatus.PENDING:
        await callback.message.answer("ℹ️ Этот платёж уже обработан.")
        await callback.message.edit_reply_markup(reply_markup=None)
        return

    result = await session.execute(select(User).where(User.tg_id == payment.user_tg_id))
    user = result.scalar_one_or_none()

    if action == "approve":
        payment.status = PaymentStatus.APPROVED
        payment.confirmed_by = callback.from_user.id
        payment.confirmed_at = callback.message.date
        if user:
            user.is_active = True
        await session.commit()

        invite_link = await generate_invite_link(callback.bot)

        if user:
            await callback.bot.send_message(
                user.tg_id,
                PAYMENT_APPROVED.format(invite_link=invite_link),
            )

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(
            f"✅ Платёж №{payment_id} подтверждён.\n"
            f"Ссылка отправлена пользователю."
        )

    elif action == "reject":
        payment.status = PaymentStatus.REJECTED
        payment.confirmed_by = callback.from_user.id
        payment.confirmed_at = callback.message.date
        await session.commit()

        if user:
            await callback.bot.send_message(
                user.tg_id,
                PAYMENT_REJECTED.format(support=settings.SUPPORT_USERNAME),
            )

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.answer(f"❌ Платёж №{payment_id} отклонён.")

    else:
        await callback.message.answer("⚠️ Неизвестное действие.")