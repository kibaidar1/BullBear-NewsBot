"""Сервис фильтрации новостей"""
from typing import Dict, List
import re


class NewsFilter:
    """Класс для фильтрации релевантности новостей"""

    @staticmethod
    def is_relevant(
            article: Dict,
            company_name: str,
            exclude_keywords: List[str] = None,
            include_keywords: List[str] = None
    ) -> bool:
        """
        Проверить релевантность новости

        Args:
            article: Статья из GNews API
            company_name: Название компании
            exclude_keywords: Список слов-исключений
            include_keywords: Список обязательных слов

        Returns:
            True если новость релевантна, False иначе
        """
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        content = article.get('content', '').lower()

        full_text = f"{title} {description} {content}"

        # Проверка слов-исключений
        if exclude_keywords:
            for keyword in exclude_keywords:
                # Используем word boundary для точного совпадения
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if re.search(pattern, full_text):
                    return False

        # Проверка обязательных слов
        if include_keywords:
            for keyword in include_keywords:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                if not re.search(pattern, full_text):
                    return False

        return True

    @staticmethod
    def calculate_relevance_score(article: Dict, company_name: str) -> float:
        """
        Вычислить оценку релевантности новости (0.0 - 1.0)

        Основано на:
        - Упоминание в заголовке (высокий вес)
        - Упоминание в описании (средний вес)
        - Позиция упоминания (чем раньше, тем лучше)
        """
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()

        company_lower = company_name.lower()
        score = 0.0

        # Упоминание в заголовке = +0.5
        if company_lower in title:
            score += 0.5
            # Если в начале заголовка = дополнительные очки
            if title.startswith(company_lower):
                score += 0.2

        # Упоминание в описании = +0.3
        if company_lower in description:
            score += 0.3
            # Чем раньше упоминается, тем лучше
            position = description.find(company_lower)
            if position < len(description) * 0.3:  # В первой трети
                score += 0.2

        return min(score, 1.0)  # Ограничиваем максимум 1.0

    @staticmethod
    def get_common_exclusions(company_name: str) -> List[str]:
        """
        Получить рекомендуемые исключения для популярных компаний
        """
        exclusion_map = {
            'яндекс': ['карты', 'такси', 'маркет', 'музыка', 'браузер', 'диск', 'еда'],
            'google': ['maps', 'chrome', 'play', 'drive', 'photos', 'meet'],
            'amazon': ['prime', 'kindle', 'alexa', 'aws'],
            'microsoft': ['office', 'teams', 'azure', 'xbox'],
        }

        company_lower = company_name.lower()
        for key, exclusions in exclusion_map.items():
            if key in company_lower:
                return exclusions

        return []
