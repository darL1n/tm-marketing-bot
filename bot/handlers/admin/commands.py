from io import BytesIO

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message
from sqlalchemy import func, select

from bot.models.payment import Payment, PaymentStatus
from bot.models.user import User
from bot.services.export import export_users_csv
from bot.services.invite import generate_invite_link

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message, session):
    users_count   = await session.scalar(select(func.count()).select_from(User))
    payments_all  = await session.scalar(select(func.count()).select_from(Payment))
    payments_ok   = await session.scalar(
        select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.APPROVED)
    )
    pending_count = await session.scalar(
        select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.PENDING)
    )
    await message.answer(
        "📊 <b>Статистика TM.Academy</b>\n\n"
        f"👤 Пользователей: {users_count}\n"
        f"✅ Оплачено: {payments_ok}\n"
        f"⏳ Ожидает проверки: {pending_count}\n"
        f"📋 Всего заявок: {payments_all}"
    )


@router.message(Command("users"))
async def cmd_users(message: Message, session):
    csv_text = await export_users_csv(session)
    file = BufferedInputFile(csv_text.encode("utf-8"), filename="users.csv")
    await message.answer_document(document=file, caption="📋 Список пользователей")


@router.message(Command("grant"))
async def cmd_grant(message: Message, session):
    """
    /grant <telegram_id>  — выдать доступ вручную
    """
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Использование: /grant <telegram_id>")
        return

    tg_id = int(parts[1])
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer(f"⚠️ Пользователь {tg_id} не найден в базе.")
        return

    user.is_active = True
    await session.commit()

    invite_link = await generate_invite_link(message.bot)
    await message.answer(f"✅ Доступ выдан пользователю <code>{tg_id}</code>.")

    try:
        await message.bot.send_message(
            tg_id,
            f"🎉 Вам выдан доступ к TM.Academy!\n\nСсылка на канал:\n{invite_link}",
        )
    except Exception:
        await message.answer("⚠️ Не удалось отправить сообщение пользователю (возможно, не начинал диалог с ботом).")


@router.message(Command("revoke"))
async def cmd_revoke(message: Message, session):
    """
    /revoke <telegram_id>  — забрать доступ
    """
    parts = message.text.split()
    if len(parts) != 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Использование: /revoke <telegram_id>")
        return

    tg_id = int(parts[1])
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer(f"⚠️ Пользователь {tg_id} не найден в базе.")
        return

    user.is_active = False
    await session.commit()
    await message.answer(f"🚫 Доступ отозван у пользователя <code>{tg_id}</code>.")

    try:
        await message.bot.send_message(
            tg_id,
            "ℹ️ Ваш доступ к TM.Academy был отозван. Если это ошибка — свяжитесь с поддержкой.",
        )
    except Exception:
        pass


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🛠 <b>Команды администратора</b>\n\n"
        "/stats — статистика\n"
        "/users — выгрузить CSV со всеми пользователями\n"
        "/grant <code>tg_id</code> — выдать доступ вручную\n"
        "/revoke <code>tg_id</code> — отозвать доступ\n"
    )