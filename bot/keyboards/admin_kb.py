from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def review_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Подтвердить",
                callback_data=f"review:approve:{payment_id}",
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"review:reject:{payment_id}",
            ),
        ]
    ])