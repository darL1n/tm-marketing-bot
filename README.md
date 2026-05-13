# TM.Academy Bot

Простой Telegram-бот для продажи доступа к курсу TM.Academy.

## Стек

- Python 3.11+
- aiogram 3.x
- PostgreSQL + asyncpg
- SQLAlchemy 2.0 async
- Alembic
- Redis
- loguru
- pydantic-settings

## Установка

### С Docker Compose (рекомендуется)

1. Скопируйте окружение:

```bash
cp .env.example .env
```

2. Обновите `BOT_TOKEN` в `.env`

3. Запустите зависимости (PostgreSQL + Redis):

```bash
docker-compose up -d
```

4. Установите зависимости Python локально:

```bash
pip install -r requirements.txt
```

5. Запустите миграции:

```bash
alembic upgrade head
```

6. Запустите бота:

```bash
python -m bot.main
```

### Локальная установка

1. Скопируйте окружение:

```bash
cp .env.example .env
```

2. Установите и запустите PostgreSQL 15+:

```bash
# macOS
brew install postgresql@15
brew services start postgresql@15

# Linux
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

3. Создайте базу данных:

```bash
createdb tm_academy
```

4. Установите Redis:

```bash
# macOS
brew install redis
brew services start redis

# Linux
sudo apt install redis-server
sudo systemctl start redis-server
```

5. Установите зависимости Python:

```bash
pip install -r requirements.txt
```

6. Настройте `.env`:

```env
BOT_TOKEN=your_bot_token
ADMIN_IDS=[123456789]
ADMIN_CHAT_ID=123456789
CHANNEL_ID=-1001234567890
DB_NAME=tm_academy
DB_USER=your_username
DB_PASS=your_password
```

7. Запустите миграции:

```bash
alembic upgrade head
```

8. Запустите бота:

```bash
python -m bot.main
```

## Миграции

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```

## Структура

- `bot/` — код бота
- `migrations/` — миграции Alembic
- `.env.example` — пример переменных окружения
