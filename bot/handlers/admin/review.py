from aiogram import F, Router
from aiogram.types import CallbackQuery
from datetime import datetime, timedelta, timezone
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.settings import settings
from bot.keyboards.admin_kb import review_keyboard
from bot.models.payment import Payment, PaymentStatus
from bot.models.user import User
from bot.services.invite import generate_invite_link
from bot.utils.messages import PAYMENT_APPROVED, PAYMENT_REJECTED

router = Router()


def _to_naive_utc(dt):
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


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
        # Снимаем бан, если пользователь был кикнут
        try:
            await callback.bot.unban_chat_member(
                settings.CHANNEL_ID,
                payment.user_tg_id,
                only_if_banned=True,  # не трогает обычных участников
            )
            logger.debug(
                "Unban attempted for user_tg_id={user_tg_id} before invite",
                user_tg_id=payment.user_tg_id,
            )
        except Exception as exc:
            logger.warning("Failed to unban user {}: {}", payment.user_tg_id, exc)
            
        invite_link = await generate_invite_link(callback.bot)
        if invite_link is None:
            logger.error(
                "Invite creation failed for payment_id={payment_id}, user_tg_id={user_tg_id}, callback_data={callback_data}",
                payment_id=payment_id,
                user_tg_id=payment.user_tg_id,
                callback_data=callback.data,
            )
            await callback.message.answer(
                "⚠️ Не удалось создать приглашение в канал. Проверьте, что бот является администратором канала и имеет право 'Manage Invite Links'."
            )
            return

        logger.info(
            "Invite created for payment_id={payment_id}, user_tg_id={user_tg_id}",
            payment_id=payment_id,
            user_tg_id=payment.user_tg_id,
        )

        payment.status = PaymentStatus.APPROVED
        payment.confirmed_by = callback.from_user.id
        payment.confirmed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if user:
            user.is_active = True
            user.invite_link = invite_link
            user.invite_expire_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)
        await session.commit()

        if user:
            from bot.keyboards.user_kb import join_channel_keyboard

            logger.debug(
                "Sending approval to user {user_id} with invite_link={invite_link}",
                user_id=user.tg_id,
                invite_link=invite_link,
            )
            await callback.bot.send_message(
                user.tg_id,
                PAYMENT_APPROVED.format(invite_link=invite_link),
                reply_markup=join_channel_keyboard(invite_link),
            )

        admin_name = callback.from_user.full_name or callback.from_user.username or str(callback.from_user.id)
        result_note = (
            f"\n\n✅ Платёж подтверждён администратором {admin_name}.\n"
            f"Ссылка отправлена пользователю."
        )
        if callback.message.caption is not None:
            await callback.message.edit_caption(
                caption=f"{callback.message.caption}{result_note}",
                reply_markup=None,
            )
        else:
            await callback.message.edit_text(
                f"{callback.message.text or ''}{result_note}",
                reply_markup=None,
            )


    elif action == "reject":
        payment.status = PaymentStatus.REJECTED
        payment.confirmed_by = callback.from_user.id
        payment.confirmed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.commit()

        if user:
            await callback.bot.send_message(
                user.tg_id,
                PAYMENT_REJECTED.format(support=settings.SUPPORT_USERNAME),
            )

        admin_name = callback.from_user.full_name or callback.from_user.username or str(callback.from_user.id)
        result_note = (
            f"\n\n❌ Платёж отклонён администратором {admin_name}."
        )
        if callback.message.caption is not None:
            await callback.message.edit_caption(
                caption=f"{callback.message.caption}{result_note}",
                reply_markup=None,
            )
        else:
            await callback.message.edit_text(
                f"{callback.message.text or ''}{result_note}",
                reply_markup=None,
            )

        await callback.message.answer(f"❌ Платёж №{payment_id} отклонён.")

    else:
        await callback.message.answer("⚠️ Неизвестное действие.")