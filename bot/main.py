import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from loguru import logger

from bot.config.settings import settings
from bot.handlers.admin import router as admin_router
from bot.handlers.user import router as user_router
from bot.middlewares.admin_check import AdminMiddleware
from bot.middlewares.db import DbSessionMiddleware
from bot.models.base import Base, engine
from bot.models.user import User  # noqa: F401
from bot.models.payment import Payment  # noqa: F401


async def on_startup(bot: Bot) -> None:
    logger.info("Starting TM.Academy Bot")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def on_shutdown(bot: Bot) -> None:
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

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    if settings.WEBHOOK_HOST:
        app = web.Application()
        SimpleRequestHandler(dispatcher=dp, bot=bot).register(
            app, path=settings.WEBHOOK_PATH
        )
        setup_application(app, dp, bot=bot)

        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host="0.0.0.0", port=8000)
        await site.start()
        logger.info("Webhook server started on port 8000")

        await asyncio.Event().wait()  # держим процесс живым
    else:
        logger.info("Starting polling mode")
        await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())