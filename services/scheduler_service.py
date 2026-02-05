"""Сервис планировщика задач"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot
from database.database import Database
from services.news_service import NewsService
from services.keepalive_service import KeepAliveService
from config import Config
import logging

logger = logging.getLogger(__name__)


class SchedulerService:
    """Сервис для периодической проверки новостей"""

    def __init__(
        self,
        bot: Bot,
        database: Database,
        news_service: NewsService,
        config: Config,
        keepalive_service: KeepAliveService = None
    ):
        self.bot = bot
        self.database = database
        self.news_service = news_service
        self.config = config
        self.keepalive_service = keepalive_service
        self.scheduler = AsyncIOScheduler()

    async def check_and_send_news(self):
        """Проверить новости и отправить пользователям"""
        logger.info("Starting news check cycle")

        try:
            subscriptions = await self.database.get_all_subscriptions()

            # Группируем подписки по компаниям
            companies_users = {}
            for user_id, company_name in subscriptions:
                if company_name not in companies_users:
                    companies_users[company_name] = []
                companies_users[company_name].append(user_id)

            # Получаем новости для каждой компании
            for company_name, user_ids in companies_users.items():
                logger.info(f"Fetching news for {company_name}")

                # Получаем фильтры первого пользователя (или можно индивидуально)
                articles = await self.news_service.fetch_news(
                    company_name,
                    max_results=3,
                    min_relevance_score=0.3
                )

                if articles:
                    for article in articles:
                        news_url = article.get('url', '')

                        for user_id in user_ids:
                            # Получаем персональные фильтры пользователя
                            filters = await self.database.get_subscription_filters(
                                user_id,
                                company_name
                            )

                            # Проверяем фильтры
                            if filters['exclude'] or filters['include']:
                                from services.news_filter import NewsFilter
                                filter_service = NewsFilter()

                                if not filter_service.is_relevant(
                                    article,
                                    company_name,
                                    filters['exclude'],
                                    filters['include']
                                ):
                                    continue

                            # Проверяем, не отправляли ли ранее
                            if not await self.database.is_news_sent(user_id, news_url):
                                await self.send_news_to_user(user_id, company_name, article)
                                await self.database.mark_news_as_sent(user_id, news_url)
                                await asyncio.sleep(0.5)

                await asyncio.sleep(2)

            logger.info("News check cycle completed")

        except Exception as e:
            logger.error(f"Error in check_and_send_news: {e}", exc_info=True)

    async def send_news_to_user(self, user_id: int, company_name: str, article: dict):
        """Отправить новость пользователю"""
        try:
            message_text = self.news_service.format_news_message(company_name, article)
            await self.bot.send_message(
                user_id,
                message_text,
                parse_mode="HTML",
                disable_web_page_preview=False
            )
        except Exception as e:
            logger.error(f"Error sending message to {user_id}: {e}")

    def start(self):
        """Запустить планировщик"""
        # Основная задача проверки новостей
        self.scheduler.add_job(
            self.check_and_send_news,
            trigger=IntervalTrigger(seconds=self.config.scheduler.check_interval),
            id='news_checker',
            name='Check news for all subscriptions',
            replace_existing=True
        )

        # Очистка старых записей раз в день
        self.scheduler.add_job(
            self.database.cleanup_old_news,
            trigger=IntervalTrigger(hours=24),
            id='cleanup_old_news',
            name='Cleanup old sent news records',
            kwargs={'days': 7},
            replace_existing=True
        )

        # Keep-alive для Render (пинг каждые 10 минут)
        if self.keepalive_service and self.config.render.is_render:
            self.scheduler.add_job(
                self.keepalive_service.self_ping,
                trigger=IntervalTrigger(minutes=10),
                id='keepalive_ping',
                name='Keep-alive self ping',
                replace_existing=True
            )
            logger.info("Keep-alive ping scheduled (every 10 minutes)")

        self.scheduler.start()
        logger.info("Scheduler started")

    def shutdown(self):
        """Остановить планировщик"""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
