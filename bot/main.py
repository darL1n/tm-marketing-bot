import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from loguru import logger

from bot.config.settings import settings
from bot.handlers.admin import router as admin_router
from bot.handlers.user import router as user_router
from bot.middlewares.admin_check import AdminMiddleware
from bot.middlewares.db import DbSessionMiddleware
from bot.models.base import Base, engine


async def on_startup(bot: Bot) -> None:
    logger.info("Starting TM.Academy Bot")
    if settings.WEBHOOK_HOST:
        await bot.delete_webhook()


async def on_shutdown() -> None:
    logger.info("Shutting down")
    await engine.dispose()


async def main() -> None:
    storage = RedisStorage.from_url(settings.REDIS_URL)
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher(storage=storage)

    dp.include_router(user_router)
    dp.include_router(admin_router)

    admin_router.message.middleware(AdminMiddleware())
    admin_router.callback_query.middleware(AdminMiddleware())

    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())

    if settings.WEBHOOK_HOST:
        webhook_url = f"{settings.WEBHOOK_HOST}{settings.WEBHOOK_PATH}"
        logger.info("Starting webhook mode: {}", webhook_url)
        await dp.start_webhook(
            bot=bot,
            webhook_path=settings.WEBHOOK_PATH,
            webhook_url=webhook_url,
            skip_updates=True,
            host="0.0.0.0",
            port=8000,
            on_startup=[on_startup],
            on_shutdown=[on_shutdown],
        )
    else:
        logger.info("Starting polling mode")
        await on_startup(bot)
        await dp.start_polling(bot, skip_updates=True)
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())