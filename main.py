"""Главный файл запуска бота"""
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import load_config
from database.database import Database
from services.news_service import NewsService
from services.scheduler_service import SchedulerService
from services.keepalive_service import KeepAliveService
from middlewares.database import DatabaseMiddleware
from utils.logger import setup_logger

# Импорт роутеров
from bot.handlers import start, subscriptions, news

logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # Настройка логирования
    setup_logger()
    logger.info("Starting StockPulse News Bot...")

    # Загрузка конфигурации
    config = load_config()
    logger.info(f"Configuration loaded. Running on Render: {config.render.is_render}")

    # Инициализация бота и диспетчера
    bot = Bot(
        token=config.tg_bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация базы данных
    database = Database(config.database.path)
    await database.init_db()
    logger.info(f"Database initialized at: {config.database.path}")

    # Инициализация сервисов
    news_service = NewsService(config.gnews)

    # Keep-alive сервис (только для Render)
    keepalive_service = None
    if config.render.is_render:
        keepalive_service = KeepAliveService(
            port=config.render.port,
            external_url=config.render.external_url
        )
        await keepalive_service.start()
        logger.info(f"Keep-alive service started on port {config.render.port}")

    # Scheduler сервис
    scheduler_service = SchedulerService(
        bot,
        database,
        news_service,
        config,
        keepalive_service
    )

    # Регистрация middleware
    dp.message.middleware(DatabaseMiddleware(database))
    dp.callback_query.middleware(DatabaseMiddleware(database))

    # Добавляем сервисы в data для доступа в хендлерах
    dp['news_service'] = news_service
    dp['scheduler_service'] = scheduler_service
    dp['database'] = database

    # Регистрация роутеров
    dp.include_router(start.router)
    dp.include_router(subscriptions.router)
    dp.include_router(news.router)

    # Запуск планировщика
    scheduler_service.start()
    logger.info("Scheduler started")

    # Отправляем уведомление о старте (опционально)
    try:
        admin_id = os.getenv('ADMIN_ID')
        if admin_id:
            await bot.send_message(
                admin_id,
                "🤖 <b>StockPulse Bot запущен!</b>\n\n"
                f"Окружение: {'Render' if config.render.is_render else 'Local'}\n"
                f"База данных: {config.database.path}",
                parse_mode="HTML"
            )
    except Exception as e:
        logger.warning(f"Could not send startup notification: {e}")

    try:
        # Удаление вебхуков
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Bot started successfully! Polling mode activated.")

        # Запуск polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error(f"Error during bot execution: {e}", exc_info=True)

    finally:
        # Cleanup
        scheduler_service.shutdown()
        if keepalive_service:
            await keepalive_service.stop()
        await bot.session.close()
        logger.info("Bot stopped gracefully")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
