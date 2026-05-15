# TM.Academy Bot — Полная архитектура

## Стек

| Компонент | Технология |
|---|---|
| Язык | Python 3.11+ |
| Фреймворк бота | aiogram 3.x |
| БД | PostgreSQL 15+ |
| ORM | SQLAlchemy 2.0 async |
| Миграции | Alembic |
| Драйвер БД | asyncpg |
| Кэш / FSM Storage | Redis |
| Конфиг | pydantic-settings + .env |
| Логирование | loguru |
| Деплой | systemd + NGINX (webhook) |

---

## Файловая структура

```
tm_academy_bot/
│
├── bot/
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── user/
│   │   │   ├── __init__.py
│   │   │   ├── start.py          # /start, главное меню
│   │   │   ├── course.py         # "Что внутри курса", FAQ
│   │   │   └── payment.py        # выбор страны → карта → отправка чека
│   │   │
│   │   └── admin/
│   │       ├── __init__.py
│   │       ├── review.py         # подтвердить / отклонить оплату
│   │       └── commands.py       # /stats, /users, /grant, /revoke
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py               # DeclarativeBase, async engine
│   │   ├── user.py               # модель User
│   │   └── payment.py            # модель Payment
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── invite.py             # генерация invite-ссылки на канал
│   │   ├── subscription.py       # проверка подписки пользователя на канал
│   │   └── export.py             # выгрузка CSV со списком юзеров
│   │
│   ├── keyboards/
│   │   ├── __init__.py
│   │   ├── user_kb.py            # главное меню, выбор страны, оплата
│   │   └── admin_kb.py           # кнопки подтвердить/отклонить
│   │
│   ├── middlewares/
│   │   ├── __init__.py
│   │   ├── db.py                 # инжектирует async сессию в хэндлер
│   │   └── admin_check.py        # проверка: является ли юзер админом
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py           # pydantic-settings модель конфига
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── messages.py           # тексты сообщений (константы)
│   │   └── helpers.py            # форматирование дат, генерация текста
│   │
│   └── main.py                   # точка входа, регистрация роутеров
│
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── .env
├── .env.example
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## Конфиг — `bot/config/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Bot
    BOT_TOKEN: str
    ADMIN_IDS: list[int]          # список Telegram ID администраторов
    ADMIN_CHAT_ID: int            # чат куда бот шлёт уведомления о платежах
    CHANNEL_ID: int               # закрытый канал с курсом

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASS: str

    @property
    def db_url(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Реквизиты по странам
    CARDS: dict[str, dict] = {
        "kg": {"label": "🇰🇬 Кыргызстан", "number": "1234 5678 9012 3456", "bank": "Mbank / O!Деньги"},
        "kz": {"label": "🇰🇿 Казахстан",   "number": "9876 5432 1098 7654", "bank": "Kaspi"},
        "ru": {"label": "🇷🇺 Россия",       "number": "4444 3333 2222 1111", "bank": "SberPay / СБП"},
    }

    # Webhook (для прода)
    WEBHOOK_HOST: str = ""
    WEBHOOK_PATH: str = "/webhook"

    COURSE_PRICE: str = "XXX $"


settings = Settings()
```

---

## Модели — SQLAlchemy

### `bot/models/base.py`

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from bot.config.settings import settings

engine = create_async_engine(settings.db_url, echo=False)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass
```

### `bot/models/user.py`

```python
from datetime import datetime
from sqlalchemy import BigInteger, String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base

class User(Base):
    __tablename__ = "users"

    id:          Mapped[int]      = mapped_column(primary_key=True, autoincrement=True)
    tg_id:       Mapped[int]      = mapped_column(BigInteger, unique=True, nullable=False)
    username:    Mapped[str|None] = mapped_column(String(64))
    full_name:   Mapped[str|None] = mapped_column(String(256))
    is_active:   Mapped[bool]     = mapped_column(Boolean, default=False)   # имеет доступ к каналу
    joined_at:   Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

### `bot/models/payment.py`

```python
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, func, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column
import enum
from .base import Base

class PaymentStatus(str, enum.Enum):
    PENDING   = "pending"     # чек отправлен, ожидает проверки
    APPROVED  = "approved"    # одобрен
    REJECTED  = "rejected"    # отклонён

class Payment(Base):
    __tablename__ = "payments"

    id:             Mapped[int]           = mapped_column(primary_key=True, autoincrement=True)
    user_tg_id:     Mapped[int]           = mapped_column(BigInteger, ForeignKey("users.tg_id"))
    country:        Mapped[str]           = mapped_column(String(8))           # kg / kz / ru
    receipt_file_id:Mapped[str]           = mapped_column(String(256))         # Telegram file_id скрина
    status:         Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    created_at:     Mapped[datetime]      = mapped_column(DateTime, server_default=func.now())
    confirmed_at:   Mapped[datetime|None] = mapped_column(DateTime, nullable=True)
    confirmed_by:   Mapped[int|None]      = mapped_column(BigInteger, nullable=True)  # tg_id админа
```

---

## Middleware — инжекция сессии

### `bot/middlewares/db.py`

```python
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from bot.models.base import AsyncSessionFactory

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with AsyncSessionFactory() as session:
            data["session"] = session
            return await handler(event, data)
```

### `bot/middlewares/admin_check.py`

```python
from typing import Any, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Message
from bot.config.settings import settings

class AdminMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Message, data: dict[str, Any]) -> Any:
        if event.from_user.id not in settings.ADMIN_IDS:
            await event.answer("⛔ Нет доступа.")
            return
        return await handler(event, data)
```

---

## Сценарий оплаты (FSM)

Ключевой флоу — пошаговый, держится в Redis через FSM aiogram.

```
[Купить курс]
      │
      ▼
Выбор страны (inline-кнопки: 🇰🇬 🇰🇿 🇷🇺 ...)
      │
      ▼
Бот отправляет номер карты + сумму
"Переведите XXX $ на карту: 1234 5678 9012 3456 (Mbank)"
"После оплаты пришлите скриншот чека сюда 👇"
      │
      ▼  (FSM State: WaitingReceipt)
Пользователь присылает фото/документ
      │
      ▼
Бот:
  1. Сохраняет payment в БД (status=PENDING)
  2. Отвечает пользователю: "✅ Чек получен. Проверим в течение 5 минут."
  3. Шлёт в ADMIN_CHAT уведомление с inline-кнопками
      │
      ▼
Админ жмёт [✅ Подтвердить] или [❌ Отклонить]
      │
   ┌──┴──────────────────┐
   ▼                     ▼
Подтвердить:          Отклонить:
- payment.status      - payment.status = REJECTED
  = APPROVED          - user.is_active = False (не меняем)
- user.is_active      - Сообщение юзеру:
  = True                "Оплата не подтверждена. Если это
- Генерируем            ошибка — напишите в поддержку."
  invite_link
- Сообщение юзеру:
  "🎉 Добро пожаловать!
   Ссылка на канал: ..."
```

---

## Хэндлеры — ключевые

### `bot/handlers/user/payment.py`

```python
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.settings import settings
from bot.keyboards.user_kb import countries_keyboard
from bot.keyboards.admin_kb import review_keyboard
from bot.models.payment import Payment
from bot.models.user import User

router = Router()

class PaymentFSM(StatesGroup):
    choosing_country = State()
    waiting_receipt  = State()


@router.callback_query(F.data == "buy_course")
async def buy_course(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        f"💳 Выберите вашу страну для оплаты:",
        reply_markup=countries_keyboard()
    )
    await state.set_state(PaymentFSM.choosing_country)


@router.callback_query(PaymentFSM.choosing_country, F.data.startswith("country:"))
async def country_chosen(call: CallbackQuery, state: FSMContext):
    country_code = call.data.split(":")[1]
    card_info = settings.CARDS.get(country_code)

    if not card_info:
        await call.answer("Неизвестная страна", show_alert=True)
        return

    await state.update_data(country=country_code)
    await call.message.edit_text(
        f"💳 Реквизиты для оплаты ({card_info['label']}):\n\n"
        f"<b>{card_info['number']}</b>\n"
        f"Банк: {card_info['bank']}\n"
        f"Сумма: <b>{settings.COURSE_PRICE}</b>\n\n"
        f"После перевода пришлите сюда скриншот чека 👇",
        parse_mode="HTML"
    )
    await state.set_state(PaymentFSM.waiting_receipt)


@router.message(PaymentFSM.waiting_receipt, F.photo | F.document)
async def receipt_received(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    country = data.get("country", "unknown")

    # file_id — берём из фото или документа
    if message.photo:
        file_id = message.photo[-1].file_id
    else:
        file_id = message.document.file_id

    # Upsert пользователя
    user = await session.get(User, message.from_user.id)
    if not user:
        user = User(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
        )
        session.add(user)

    # Создаём платёж
    payment = Payment(
        user_tg_id=message.from_user.id,
        country=country,
        receipt_file_id=file_id,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)

    # Отвечаем пользователю
    await message.answer(
        "✅ Чек получен!\n"
        "Наши администраторы проверят оплату в течение 5 минут.\n"
        "Мы уведомим вас о результате."
    )

    # Уведомляем админов
    username_str = f"@{message.from_user.username}" if message.from_user.username else "без username"
    caption = (
        f"🆕 Новый чек об оплате!\n\n"
        f"👤 {message.from_user.full_name} ({username_str})\n"
        f"🆔 TG ID: <code>{message.from_user.id}</code>\n"
        f"🌍 Страна: {country.upper()}\n"
        f"💳 Сумма: {settings.COURSE_PRICE}\n"
        f"📋 Payment ID: <code>{payment.id}</code>"
    )

    if message.photo:
        await message.bot.send_photo(
            chat_id=settings.ADMIN_CHAT_ID,
            photo=file_id,
            caption=caption,
            reply_markup=review_keyboard(payment.id),
            parse_mode="HTML"
        )
    else:
        await message.bot.send_document(
            chat_id=settings.ADMIN_CHAT_ID,
            document=file_id,
            caption=caption,
            reply_markup=review_keyboard(payment.id),
            parse_mode="HTML"
        )

    await state.clear()
```

---

### `bot/handlers/admin/review.py`

```python
from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from bot.models.payment import Payment, PaymentStatus
from bot.models.user import User
from bot.services.invite import generate_invite_link

router = Router()


@router.callback_query(F.data.startswith("approve:"))
async def approve_payment(call: CallbackQuery, session: AsyncSession):
    payment_id = int(call.data.split(":")[1])

    payment = await session.get(Payment, payment_id)
    if not payment or payment.status != PaymentStatus.PENDING:
        await call.answer("Платёж уже обработан или не найден.", show_alert=True)
        return

    # Обновляем платёж
    from datetime import datetime
    payment.status       = PaymentStatus.APPROVED
    payment.confirmed_at = datetime.utcnow()
    payment.confirmed_by = call.from_user.id

    # Активируем пользователя
    user = await session.get(User, payment.user_tg_id)  # user_tg_id = primary lookup
    # На самом деле User.tg_id — используем select
    result = await session.execute(select(User).where(User.tg_id == payment.user_tg_id))
    user = result.scalar_one_or_none()
    if user:
        user.is_active = True

    await session.commit()

    # Генерируем invite-ссылку
    invite_link = await generate_invite_link(call.bot)

    # Пишем пользователю
    await call.bot.send_message(
        chat_id=payment.user_tg_id,
        text=(
            "🎉 Оплата подтверждена!\n"
            f"Добро пожаловать в TM.Academy!\n\n"
            f"🔗 Ваша ссылка на закрытый канал:\n{invite_link}\n\n"
            "⚠️ Ссылка одноразовая, не передавайте её другим."
        )
    )

    # Обновляем сообщение в чате админов
    await call.message.edit_caption(
        caption=call.message.caption + f"\n\n✅ Одобрено: @{call.from_user.username}",
        reply_markup=None
    )
    await call.answer("Доступ выдан ✅")


@router.callback_query(F.data.startswith("reject:"))
async def reject_payment(call: CallbackQuery, session: AsyncSession):
    payment_id = int(call.data.split(":")[1])

    payment = await session.get(Payment, payment_id)
    if not payment or payment.status != PaymentStatus.PENDING:
        await call.answer("Платёж уже обработан или не найден.", show_alert=True)
        return

    payment.status       = PaymentStatus.REJECTED
    payment.confirmed_by = call.from_user.id
    await session.commit()

    await call.bot.send_message(
        chat_id=payment.user_tg_id,
        text=(
            "❌ К сожалению, оплата не подтверждена.\n"
            "Если вы уверены, что перевод был сделан — напишите в поддержку.\n\n"
            "👉 @support_username"
        )
    )

    await call.message.edit_caption(
        caption=call.message.caption + f"\n\n❌ Отклонено: @{call.from_user.username}",
        reply_markup=None
    )
    await call.answer("Отклонено ❌")
```

---

## Клавиатуры

### `bot/keyboards/user_kb.py`

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.config.settings import settings

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Купить курс",       callback_data="buy_course")],
        [InlineKeyboardButton(text="📚 Что внутри курса",  callback_data="course_info")],
        [InlineKeyboardButton(text="🙋 Поддержка",         url="https://t.me/support_username")],
    ])

def countries_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for code, info in settings.CARDS.items():
        rows.append([InlineKeyboardButton(text=info["label"], callback_data=f"country:{code}")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
```

### `bot/keyboards/admin_kb.py`

```python
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def review_keyboard(payment_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"approve:{payment_id}"),
            InlineKeyboardButton(text="❌ Отклонить",   callback_data=f"reject:{payment_id}"),
        ]
    ])
```

---

## Сервисы

### `bot/services/invite.py`

```python
from aiogram import Bot
from bot.config.settings import settings

async def generate_invite_link(bot: Bot) -> str:
    """
    Создаёт одноразовую invite-ссылку на закрытый канал.
    Бот должен быть администратором канала с правом invite users.
    """
    link = await bot.create_chat_invite_link(
        chat_id=settings.CHANNEL_ID,
        member_limit=1,          # одноразовая
        creates_join_request=False,
    )
    return link.invite_link
```

### `bot/services/export.py`

```python
import csv
import io
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from bot.models.user import User

async def export_users_csv(session: AsyncSession) -> bytes:
    result = await session.execute(
        select(User).where(User.is_active == True).order_by(User.joined_at)
    )
    users = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["tg_id", "username", "full_name", "joined_at"])
    for u in users:
        writer.writerow([u.tg_id, u.username or "", u.full_name or "", u.joined_at])

    return output.getvalue().encode("utf-8-sig")  # utf-8-sig для Excel
```

---

## Команды администратора

### `bot/handlers/admin/commands.py`

```python
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from bot.models.user import User
from bot.models.payment import Payment, PaymentStatus
from bot.services.export import export_users_csv
from bot.services.invite import generate_invite_link

router = Router()


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession):
    total    = await session.scalar(select(func.count()).select_from(User))
    active   = await session.scalar(select(func.count()).select_from(User).where(User.is_active == True))
    payments = await session.scalar(select(func.count()).select_from(Payment).where(Payment.status == PaymentStatus.APPROVED))
    await message.answer(
        f"📊 Статистика:\n"
        f"👥 Всего юзеров: {total}\n"
        f"✅ Активных (с доступом): {active}\n"
        f"💳 Подтверждённых оплат: {payments}"
    )


@router.message(Command("users"))
async def cmd_users(message: Message, session: AsyncSession):
    csv_bytes = await export_users_csv(session)
    file = BufferedInputFile(csv_bytes, filename="users.csv")
    await message.answer_document(file, caption="📋 Список активных пользователей")


@router.message(Command("grant"))
async def cmd_grant(message: Message, session: AsyncSession):
    """Пример: /grant 123456789"""
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /grant <tg_id>")
        return
    tg_id = int(args[1])
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("Пользователь не найден.")
        return
    user.is_active = True
    await session.commit()
    link = await generate_invite_link(message.bot)
    await message.bot.send_message(tg_id, f"✅ Доступ выдан вручную.\n🔗 {link}")
    await message.answer(f"✅ Доступ выдан пользователю {tg_id}")


@router.message(Command("revoke"))
async def cmd_revoke(message: Message, session: AsyncSession):
    """Пример: /revoke 123456789"""
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /revoke <tg_id>")
        return
    tg_id = int(args[1])
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer("Пользователь не найден.")
        return
    user.is_active = False
    await session.commit()
    # Кикаем из канала
    try:
        await message.bot.ban_chat_member(settings.CHANNEL_ID, tg_id)
        await message.bot.unban_chat_member(settings.CHANNEL_ID, tg_id)  # бан+разбан = кик без блокировки
    except Exception as e:
        await message.answer(f"Не удалось кикнуть из канала: {e}")
    await message.answer(f"🚫 Доступ отозван у пользователя {tg_id}")
```

---

## Точка входа — `bot/main.py`

```python
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger

from bot.config.settings import settings
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.admin_check import AdminMiddleware
from bot.handlers.user import start, course, payment
from bot.handlers.admin import review, commands as admin_commands

async def main():
    bot = Bot(token=settings.BOT_TOKEN)
    storage = RedisStorage.from_url(settings.REDIS_URL)
    dp = Dispatcher(storage=storage)

    # Middleware
    dp.update.middleware(DbSessionMiddleware())

    # Роутеры — пользовательские
    dp.include_router(start.router)
    dp.include_router(course.router)
    dp.include_router(payment.router)

    # Роутеры — админские (с middleware проверки доступа)
    admin_router = admin_commands.router
    admin_router.message.middleware(AdminMiddleware())
    dp.include_router(admin_router)
    dp.include_router(review.router)  # review работает через callback, проверка через ADMIN_CHAT_ID

    logger.info("Bot started")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
```

---

## `.env.example`

```env
BOT_TOKEN=7123456789:AAH...
ADMIN_IDS=[123456789, 987654321]
ADMIN_CHAT_ID=-1001234567890
CHANNEL_ID=-1009876543210

DB_HOST=localhost
DB_PORT=5432
DB_NAME=tm_academy
DB_USER=postgres
DB_PASS=secret

REDIS_URL=redis://localhost:6379/0

WEBHOOK_HOST=https://yourdomain.com
COURSE_PRICE=99 $
```

---

## `requirements.txt`

```
aiogram==3.13.0
sqlalchemy==2.0.36
asyncpg==0.30.0
alembic==1.14.0
pydantic-settings==2.7.0
redis==5.2.0
loguru==0.7.2
```

---

## Важные нюансы

### Конкурентность при подтверждении
Если два админа одновременно нажмут "Подтвердить" — второй получит ответ "Платёж уже обработан"
(проверка `payment.status != PaymentStatus.PENDING` до коммита). Для 100% надёжности можно
добавить `SELECT ... FOR UPDATE` на строку платежа.

### Хранение чеков
Используем `file_id` от Telegram — не скачиваем файлы на сервер. Минус: file_id привязан к боту
и может протухнуть если бот переедет. Для архива — скачивать и хранить в S3/локально.

### Безопасность админских команд
`AdminMiddleware` проверяет `ADMIN_IDS`. Для команд в админ-чате (`review.py`) дополнительно
проверяй `call.message.chat.id == settings.ADMIN_CHAT_ID`, чтобы кто угодно не мог
нажать approve если случайно получил payment_id.

### Кик из канала при /revoke
Telegram API: `ban` + `unban` = кик без постоянной блокировки. Бот обязан быть администратором
канала с правом "Блокировать пользователей".

### Alembic init
```bash
alembic init migrations
# в migrations/env.py указать target_metadata = Base.metadata
alembic revision --autogenerate -m "init"
alembic upgrade head
```
```
