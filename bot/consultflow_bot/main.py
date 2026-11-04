"""Точка входа Telegram-бота ConsultFlow."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from consultflow_bot.api import ConsultFlowAPI
from consultflow_bot.config import get_settings
from consultflow_bot.handlers import common, fallback, manager, my_orders, order
from consultflow_bot.notifications import notification_worker

logger = logging.getLogger(__name__)


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = get_settings()

    if not settings.is_configured:
        logger.error(
            "BOT_TOKEN не задан. Получите токен у @BotFather и укажите его в .env "
            "(BOT_TOKEN=123456:ABC...)."
        )
        return

    api = ConsultFlowAPI(
        settings.backend_url, settings.bot_api_token, settings.request_timeout
    )
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(common.router)
    dispatcher.include_router(order.router)
    dispatcher.include_router(my_orders.router)
    dispatcher.include_router(manager.router)
    dispatcher.include_router(fallback.router)

    worker = asyncio.create_task(
        notification_worker(bot, api, settings.notifications_interval)
    )
    try:
        me = await bot.get_me()
        logger.info("ConsultFlow-бот запущен: @%s", me.username)
        await bot.delete_webhook(drop_pending_updates=True)
        await dispatcher.start_polling(bot, api=api)
    finally:
        worker.cancel()
        await api.close()
        await bot.session.close()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")


if __name__ == "__main__":
    main()
