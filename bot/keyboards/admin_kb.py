from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def review_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"review:approve:{payment_id}"),
            InlineKeyboardButton(text="❌ Отклонить",   callback_data=f"review:reject:{payment_id}"),
        ]
    ])


def members_keyboard(users: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    rows = []
    for user in users:
        name = user.full_name or str(user.tg_id)
        suffix = f" @{user.username}" if user.username else ""
        rows.append([InlineKeyboardButton(
            text=f"🚫 {name}{suffix}",
            callback_data=f"members:confirm:{user.tg_id}:{page}",
        )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Пред", callback_data=f"members:page:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="След ▶️", callback_data=f"members:page:{page + 1}"))
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_revoke_keyboard(tg_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Да, исключить", callback_data=f"members:do:{tg_id}:{page}"),
        InlineKeyboardButton(text="◀️ Отмена",        callback_data=f"members:cancel:{page}"),
    ]])