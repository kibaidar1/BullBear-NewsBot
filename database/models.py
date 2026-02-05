"""Модели данных"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Модель пользователя"""
    user_id: int
    username: Optional[str]
    created_at: datetime


@dataclass
class Subscription:
    """Модель подписки"""
    id: Optional[int]
    user_id: int
    company_name: str
    created_at: datetime


@dataclass
class SentNews:
    """Модель отправленной новости"""
    id: Optional[int]
    user_id: int
    news_url: str
    sent_at: datetime
