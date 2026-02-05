"""Сервис для работы с новостями"""
import aiohttp
from typing import List, Dict, Optional
from config import GNewsConfig
from services.news_filter import NewsFilter


class NewsService:
    """Сервис для получения новостей через GNews API"""

    def __init__(self, config: GNewsConfig):
        self.config = config
        self.filter = NewsFilter()

    async def fetch_news(
        self,
        company_name: str,
        max_results: Optional[int] = None,
        exclude_keywords: List[str] = None,
        include_keywords: List[str] = None,
        min_relevance_score: float = 0.0
    ) -> List[Dict]:
        """
        Получить отфильтрованные новости по компании

        Args:
            company_name: Название компании
            max_results: Максимум результатов
            exclude_keywords: Слова для исключения
            include_keywords: Обязательные слова
            min_relevance_score: Минимальный порог релевантности (0.0-1.0)
        """
        max_results = max_results or self.config.max_results

        # Запрашиваем больше результатов для последующей фильтрации
        fetch_count = max_results * 3

        params = {
            'q': company_name,
            'token': self.config.api_key,
            'lang': self.config.language,
            'max': fetch_count,
            'sortby': 'publishedAt'
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.config.base_url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        articles = data.get('articles', [])

                        # Фильтруем и сортируем по релевантности
                        filtered_articles = []

                        for article in articles:
                            # Проверяем ключевые слова
                            if not self.filter.is_relevant(
                                article,
                                company_name,
                                exclude_keywords,
                                include_keywords
                            ):
                                continue

                            # Вычисляем релевантность
                            score = self.filter.calculate_relevance_score(
                                article,
                                company_name
                            )

                            if score >= min_relevance_score:
                                article['_relevance_score'] = score
                                filtered_articles.append(article)

                        # Сортируем по релевантности
                        filtered_articles.sort(
                            key=lambda x: x.get('_relevance_score', 0),
                            reverse=True
                        )

                        return filtered_articles[:max_results]
                    else:
                        print(f"Error fetching news: {response.status}")
                        return []
        except Exception as e:
            print(f"Exception while fetching news: {e}")
            return []

    @staticmethod
    def format_news_message(
        company_name: str,
        article: Dict,
        show_relevance: bool = False
    ) -> str:
        """Форматировать новость для отправки"""
        title = article.get('title', 'Без заголовка')
        description = article.get('description', '')
        published_at = article.get('publishedAt', '')
        source = article.get('source', {}).get('name', 'Неизвестный источник')
        url = article.get('url', '')

        message = f"""
                    📰 <b>Новости по: {company_name}</b>
                    
                    📌 <b>{title}</b>
                    
                    {description}
                    
                    🔗 Источник: {source}
                    ⏰ {published_at}
                """

        # Опционально показываем оценку релевантности
        if show_relevance and '_relevance_score' in article:
            score = article['_relevance_score']
            stars = '⭐' * int(score * 5)
            message += f"📊 Релевантность: {stars} ({score:.2f})\n"

        message += f"\n<a href=\"{url}\">Читать полностью</a>"

        return message.strip()
