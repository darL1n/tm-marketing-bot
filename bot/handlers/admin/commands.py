from datetime import datetime, timedelta
from io import BytesIO

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message, CallbackQuery
from loguru import logger
from sqlalchemy import select

from bot.config.settings import settings
from bot.models.payment import Payment, PaymentStatus
from bot.models.user import User
from bot.keyboards.admin_kb import members_keyboard, confirm_revoke_keyboard
from bot.services.export import export_users_csv
from bot.services.invite import generate_invite_link, revoke_invite_link

router = Router()

_MEMBERS_PAGE_SIZE = 5


# ── Общий хелпер: отозвать доступ ─────────────────────────────────────────────

async def _do_revoke(bot, session, tg_id: int) -> str:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        return f"⚠️ Пользователь <code>{tg_id}</code> не найден в базе."

    invite_link = user.invite_link
    user.is_active = False
    user.invite_link = None
    user.invite_expire_at = None
    await session.commit()

    if invite_link:
        await revoke_invite_link(bot, invite_link)

    try:
        await bot.ban_chat_member(settings.CHANNEL_ID, tg_id)
        await bot.unban_chat_member(settings.CHANNEL_ID, tg_id)
    except Exception as exc:
        logger.warning("Failed to kick user {} from channel: {}", tg_id, exc)

    try:
        await bot.send_message(
            tg_id,
            "ℹ️ Ваш доступ к TM.Academy был отозван. Если это ошибка — свяжитесь с поддержкой.",
        )
    except Exception:
        pass

    name = user.full_name or str(tg_id)
    return f"🚫 Доступ отозван у пользователя <code>{tg_id}</code> ({name})."


# ── Хелпер: получить страницу активных пользователей ──────────────────────────

async def _members_page_data(session, page: int):
    """Возвращает (page_users, total, page, total_pages)."""
    result = await session.execute(
        select(User).where(User.is_active == True).order_by(User.id)
    )
    users = result.scalars().all()
    total = len(users)
    if total == 0:
        return [], 0, 0, 0
    total_pages = (total + _MEMBERS_PAGE_SIZE - 1) // _MEMBERS_PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    start = page * _MEMBERS_PAGE_SIZE
    return users[start : start + _MEMBERS_PAGE_SIZE], total, page, total_pages


def _members_text(total: int, page: int, total_pages: int) -> str:
    return (
        f"👥 <b>Активные пользователи</b>\n"
        f"Всего: {total}  |  Страница {page + 1}/{total_pages}\n\n"
        f"Нажмите на пользователя чтобы исключить его из канала."
    )


# ── /members ──────────────────────────────────────────────────────────────────

@router.message(Command("members"))
async def cmd_members(message: Message, session):
    page_users, total, page, total_pages = await _members_page_data(session, 0)
    if not page_users:
        await message.answer("👥 Нет активных пользователей.")
        return
    await message.answer(
        _members_text(total, page, total_pages),
        reply_markup=members_keyboard(page_users, page, total_pages),
    )


@router.callback_query(F.data.startswith("members:page:"))
async def members_page(callback: CallbackQuery, session):
    await callback.answer()
    page = int(callback.data.split(":")[2])
    page_users, total, page, total_pages = await _members_page_data(session, page)
    if not page_users:
        await callback.message.edit_text("👥 Нет активных пользователей.")
        return
    await callback.message.edit_text(
        _members_text(total, page, total_pages),
        reply_markup=members_keyboard(page_users, page, total_pages),
    )


@router.callback_query(F.data.startswith("members:confirm:"))
async def members_confirm(callback: CallbackQuery, session):
    await callback.answer()
    _, _, tg_id_str, page_str = callback.data.split(":")
    tg_id = int(tg_id_str)
    page = int(page_str)

    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        await callback.message.edit_text("ℹ️ Пользователь уже не активен.")
        return

    name = user.full_name or str(tg_id)
    suffix = f" @{user.username}" if user.username else ""
    await callback.message.edit_text(
        f"❓ Исключить пользователя из канала?\n\n"
        f"👤 {name}{suffix}\n"
        f"🆔 <code>{tg_id}</code>",
        reply_markup=confirm_revoke_keyboard(tg_id, page),
    )


@router.callback_query(F.data.startswith("members:do:"))
async def members_do_revoke(callback: CallbackQuery, session):
    await callback.answer()
    _, _, tg_id_str, page_str = callback.data.split(":")
    tg_id = int(tg_id_str)
    page = int(page_str)

    result_text = await _do_revoke(callback.bot, session, tg_id)
    logger.info("Admin {} revoked access for tg_id={}", callback.from_user.id, tg_id)

    # Показываем результат, затем возвращаем список
    page_users, total, page, total_pages = await _members_page_data(session, page)
    if not page_users:
        await callback.message.edit_text(f"{result_text}\n\n👥 Активных пользователей больше нет.")
        return

    await callback.message.edit_text(
        f"{result_text}\n\n" + _members_text(total, page, total_pages),
        reply_markup=members_keyboard(page_users, page, total_pages),
    )


@router.callback_query(F.data.startswith("members:cancel:"))
async def members_cancel(callback: CallbackQuery, session):
    await callback.answer()
    page = int(callback.data.split(":")[2])
    page_users, total, page, total_pages = await _members_page_data(session, page)
    if not page_users:
        await callback.message.edit_text("👥 Нет активных пользователей.")
        return
    await callback.message.edit_text(
        _members_text(total, page, total_pages),
        reply_markup=members_keyboard(page_users, page, total_pages),
    )


# ── /stats ────────────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(message: Message, session):
    from sqlalchemy import func
    users_count   = await session.scalar(select(func.count()).select_from(User))
    payments_ok   = await session.scalar(
        select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.APPROVED)
    )
    pending_count = await session.scalar(
        select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.PENDING)
    )
    payments_all  = await session.scalar(select(func.count()).select_from(Payment))
    await message.answer(
        "📊 <b>Статистика TM.Academy</b>\n\n"
        f"👤 Пользователей: {users_count}\n"
        f"✅ Оплачено: {payments_ok}\n"
        f"⏳ Ожидает проверки: {pending_count}\n"
        f"📋 Всего заявок: {payments_all}"
    )


# ── /users ────────────────────────────────────────────────────────────────────

@router.message(Command("users"))
async def cmd_users(message: Message, session):
    csv_text = await export_users_csv(session)
    file = BufferedInputFile(csv_text.encode("utf-8"), filename="users.csv")
    await message.answer_document(document=file, caption="📋 Список пользователей")


# ── /grant ────────────────────────────────────────────────────────────────────

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

    try:
        await message.bot.unban_chat_member(settings.CHANNEL_ID, tg_id, only_if_banned=True)
    except Exception as exc:
        logger.warning("Failed to unban user {} before grant: {}", tg_id, exc)

    invite_link = await generate_invite_link(message.bot)
    if invite_link is None:
        logger.error("Invite creation failed for grant command: tg_id={}", tg_id)
        await message.answer("⚠️ Не удалось создать приглашение. Проверьте права бота в канале.")
        return

    user.is_active = True
    user.invite_link = invite_link
    user.invite_expire_at = datetime.utcnow() + timedelta(hours=24)
    await session.commit()

    await message.answer(f"✅ Доступ выдан пользователю <code>{tg_id}</code>.")

    try:
        await message.bot.send_message(
            tg_id,
            f"🎉 Вам выдан доступ к TM.Academy!\n\nСсылка на канал:\n{invite_link}",
        )
    except Exception:
        await message.answer("⚠️ Не удалось отправить сообщение пользователю (возможно, не начинал диалог с ботом).")


# ── /revoke ───────────────────────────────────────────────────────────────────

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
    result_text = await _do_revoke(message.bot, session, tg_id)
    await message.answer(result_text)


# ── /help ─────────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "🛠 <b>Команды администратора</b>\n\n"
        "/stats — статистика\n"
        "/users — выгрузить CSV со всеми пользователями\n"
        "/members — список активных пользователей с возможностью исключить\n"
        "/grant <code>tg_id</code> — выдать доступ вручную\n"
        "/revoke <code>tg_id</code> — отозвать доступ\n"
    )