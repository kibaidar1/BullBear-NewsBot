"""Middleware для работы с базой данных"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from database.database import Database


class DatabaseMiddleware(BaseMiddleware):
    """Middleware для добавления объекта БД в контекст"""

    def __init__(self, database: Database):
        super().__init__()
        self.database = database

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        # Добавляем объект БД в контекст
        data['db'] = self.database
        return await handler(event, data)
