from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.settings import settings


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить курс",        callback_data="buy_course")],
        [InlineKeyboardButton(text="📚 Что внутри курса",   callback_data="course")],
        [InlineKeyboardButton(text="🛠 Поддержка",          callback_data="support")],
    ])


def active_main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Что внутри курса",   callback_data="course")],
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
        [InlineKeyboardButton(text="🇺🇿 Узбекистан", callback_data="country:uz")],
        [InlineKeyboardButton(text="💳 Visa",        callback_data="country:visa")],
        [InlineKeyboardButton(text="💳 Mastercard",  callback_data="country:mastercard")],
        [InlineKeyboardButton(text="◀️ Назад",        callback_data="buy_course")],
    ])


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")],
    ])

def join_channel_keyboard(invite_link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚪 Вступить", url=invite_link)],
    ])

def faq_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="menu")],
    ])