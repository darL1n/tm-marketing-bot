from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select

from bot.config.settings import settings
from bot.keyboards.admin_kb import review_keyboard
from bot.keyboards.user_kb import (
    back_to_menu_keyboard,
    buy_keyboard,
    countries_keyboard,
)
from bot.models.payment import Payment
from bot.models.user import User
from bot.services.subscription import is_subscribed
from bot.utils.helpers import get_receipt_file_id
from bot.utils.messages import (
    BUY_INFO,
    CHOOSE_COUNTRY,
    NOT_SUBSCRIBED,
    RECEIPT_RECEIVED,
    REQUISITES,
    ADMIN_NEW_PAYMENT,
)

router = Router()


class PaymentFSM(StatesGroup):
    choosing_country = State()
    waiting_receipt = State()


# ── Экран "Купить курс" ────────────────────────────────────────────────────────

@router.callback_query(F.data == "buy_course")
async def buy_course_screen(callback: CallbackQuery, state: FSMContext):
    """Показываем описание + цену. Подписка проверяется здесь."""
    await callback.answer()
    await state.clear()

    subscribed = await is_subscribed(callback.bot, callback.from_user.id)
    if not subscribed:
        await callback.message.edit_text(
            NOT_SUBSCRIBED.format(channel_link=settings.CHANNEL_LINK),
            reply_markup=back_to_menu_keyboard(),
        )
        return

    await callback.message.edit_text(
        BUY_INFO.format(price=settings.COURSE_PRICE),
        reply_markup=buy_keyboard(),
    )


# ── Выбор страны ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "start_payment")
async def start_payment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(PaymentFSM.choosing_country)
    await callback.message.edit_text(
        CHOOSE_COUNTRY,
        reply_markup=countries_keyboard(),
    )


@router.callback_query(F.data.startswith("country:"), PaymentFSM.choosing_country)
async def country_selected(callback: CallbackQuery, state: FSMContext):
    country = callback.data.split(":", 1)[1]
    card = settings.CARDS.get(country)

    if not card:
        await callback.answer("Неверный выбор страны.", show_alert=True)
        return

    await state.update_data(country=country)
    await state.set_state(PaymentFSM.waiting_receipt)
    await callback.answer()
    await callback.message.edit_text(
        REQUISITES.format(
            price=settings.COURSE_PRICE,
            card_number=card["number"],
            bank=card["bank"],
        ),
        reply_markup=back_to_menu_keyboard(),
    )


# ── Приём чека ────────────────────────────────────────────────────────────────

@router.message(PaymentFSM.waiting_receipt, F.photo | F.document)
async def upload_receipt(message: Message, state: FSMContext, session):
    data = await state.get_data()
    country = data.get("country")
    file_id = get_receipt_file_id(message)

    if not country or not file_id:
        await message.answer("Произошла ошибка. Попробуйте ещё раз.")
        return

    # Upsert пользователя
    result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        session.add(user)

    payment = Payment(
        user_tg_id=message.from_user.id,
        country=country,
        receipt_file_id=file_id,
    )
    session.add(payment)
    await session.commit()
    await state.clear()

    # Ответ пользователю
    await message.answer(RECEIPT_RECEIVED)

    # Уведомление в админ-чат: сначала пересылаем скриншот...
    card = settings.CARDS[country]
    caption = ADMIN_NEW_PAYMENT.format(
        full_name=message.from_user.full_name or "—",
        username=message.from_user.username or "—",
        tg_id=message.from_user.id,
        country_label=card["label"],
        price=settings.COURSE_PRICE,
        payment_id=payment.id,
    )

    if message.photo:
        await message.bot.send_photo(
            chat_id=settings.ADMIN_CHAT_ID,
            photo=file_id,
            caption=caption,
            reply_markup=review_keyboard(payment.id),
        )
    else:
        # Документ (pdf / другой файл)
        await message.bot.send_document(
            chat_id=settings.ADMIN_CHAT_ID,
            document=file_id,
            caption=caption,
            reply_markup=review_keyboard(payment.id),
        )


# ── Защита: пользователь пишет текст вместо чека ──────────────────────────────

@router.message(PaymentFSM.waiting_receipt)
async def wrong_receipt_type(message: Message):
    await message.answer(
        "📎 Пожалуйста, пришлите <b>скриншот</b> (фото) или файл чека об оплате."
    )