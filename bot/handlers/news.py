"""Обработчики проверки новостей"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from database.database import Database
from services.news_service import NewsService
import asyncio

router = Router()


@router.message(Command("check"))
async def cmd_check_news(message: Message, db: Database, news_service: NewsService):
    """Проверить новости с фильтрацией"""
    user_id = message.from_user.id
    subscriptions = await db.get_user_subscriptions(user_id)

    if not subscriptions:
        await message.answer("У вас нет подписок. Используйте /add <компания>")
        return

    status_msg = await message.answer("🔍 Ищу релевантные новости...")

    news_count = 0
    for company in subscriptions:
        # Получаем фильтры для компании
        filters = await db.get_subscription_filters(user_id, company)

        # Получаем отфильтрованные новости
        articles = await news_service.fetch_news(
            company,
            max_results=3,
            exclude_keywords=filters['exclude'],
            include_keywords=filters['include'],
            min_relevance_score=0.3  # Минимальный порог релевантности
        )

        if articles:
            for article in articles:
                news_url = article.get('url', '')

                if not await db.is_news_sent(user_id, news_url):
                    message_text = news_service.format_news_message(
                        company,
                        article,
                        show_relevance=True  # Показываем оценку
                    )
                    await message.answer(message_text, parse_mode="HTML")
                    await db.mark_news_as_sent(user_id, news_url)
                    news_count += 1
                    await asyncio.sleep(0.5)

        await asyncio.sleep(1)

    await status_msg.delete()

    if news_count == 0:
        await message.answer("📭 Релевантных новостей не найдено.")
    else:
        await message.answer(f"✅ Найдено релевантных новостей: {news_count}")


@router.callback_query(F.data == "check_news")
async def callback_check_news(
        callback: CallbackQuery,
        db: Database,
        news_service: NewsService
):
    """Проверить новости через callback"""
    await callback.answer("🔍 Ищу новости...", show_alert=False)

    user_id = callback.from_user.id
    subscriptions = await db.get_user_subscriptions(user_id)

    if not subscriptions:
        await callback.message.answer(
            "У вас нет подписок. Используйте кнопку «Добавить компанию»"
        )
        return

    news_count = 0
    for company in subscriptions:
        articles = await news_service.fetch_news(company, max_results=3)

        if articles:
            for article in articles:
                news_url = article.get('url', '')

                if not await db.is_news_sent(user_id, news_url):
                    message_text = news_service.format_news_message(company, article)
                    await callback.message.answer(message_text, parse_mode="HTML")
                    await db.mark_news_as_sent(user_id, news_url)
                    news_count += 1
                    await asyncio.sleep(0.5)

        await asyncio.sleep(1)

    if news_count == 0:
        await callback.message.answer("📭 Новых новостей пока нет.")
    else:
        await callback.message.answer(f"✅ Найдено новостей: {news_count}")
