from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.settings import settings


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить курс",        callback_data="buy_course")],
        [InlineKeyboardButton(text="📚 Что внутри курса",   callback_data="course")],
        [InlineKeyboardButton(text="📢 Telegram канал",     url=settings.CHANNEL_LINK)],
        [InlineKeyboardButton(text="🛠 Поддержка",          callback_data="support")],
    ])


def buy_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить курс", callback_data="start_payment")],
        [InlineKeyboardButton(text="◀️ Назад",         callback_data="menu")],
    ])


def countries_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇰🇬 Кыргызстан", callback_data="country:kg")],
        [InlineKeyboardButton(text="🇰🇿 Казахстан",  callback_data="country:kz")],
        [InlineKeyboardButton(text="🇷🇺 Россия",      callback_data="country:ru")],
        [InlineKeyboardButton(text="◀️ Назад",        callback_data="buy_course")],
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")],
    ])


def faq_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")],
    ])