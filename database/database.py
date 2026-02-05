"""Управление базой данных"""
import aiosqlite
from typing import List, Optional


class Database:
    """Класс для работы с базой данных"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица подписок
            await db.execute('''
                CREATE TABLE IF NOT EXISTS subscriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    company_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, company_name)
                )
            ''')

            # Таблица отправленных новостей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS sent_news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    news_url TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, news_url)
                )
            ''')

            # Таблица подписок с фильтрами
            await db.execute('''
                        CREATE TABLE IF NOT EXISTS subscriptions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            company_name TEXT,
                            exclude_keywords TEXT,  -- JSON список слов-исключений
                            include_keywords TEXT,  -- JSON список обязательных слов
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(user_id),
                            UNIQUE(user_id, company_name)
                        )
                    ''')

            await db.commit()

    async def add_user(self, user_id: int, username: Optional[str] = None) -> bool:
        """Добавить пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    'INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)',
                    (user_id, username)
                )
                await db.commit()
                return True
            except Exception as e:
                print(f"Error adding user: {e}")
                return False

    async def add_subscription(
            self,
            user_id: int,
            company_name: str,
            exclude_keywords: list = None,
            include_keywords: list = None
    ) -> bool:
        """Добавить подписку с фильтрами"""
        import json

        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    '''INSERT INTO subscriptions 
                       (user_id, company_name, exclude_keywords, include_keywords) 
                       VALUES (?, ?, ?, ?)''',
                    (
                        user_id,
                        company_name,
                        json.dumps(exclude_keywords or [], ensure_ascii=False),
                        json.dumps(include_keywords or [], ensure_ascii=False)
                    )
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def remove_subscription(self, user_id: int, company_name: str) -> bool:
        """Удалить подписку"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'DELETE FROM subscriptions WHERE user_id = ? AND company_name = ?',
                (user_id, company_name)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_user_subscriptions(self, user_id: int) -> List[str]:
        """Получить подписки пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                    'SELECT company_name FROM subscriptions WHERE user_id = ? ORDER BY created_at',
                    (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def get_all_subscriptions(self) -> List[tuple]:
        """Получить все подписки"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                    'SELECT user_id, company_name FROM subscriptions'
            ) as cursor:
                return await cursor.fetchall()

    async def get_subscription_filters(self, user_id: int, company_name: str) -> dict:
        """Получить фильтры для подписки"""
        import json

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                    '''SELECT exclude_keywords, include_keywords 
                       FROM subscriptions 
                       WHERE user_id = ? AND company_name = ?''',
                    (user_id, company_name)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        'exclude': json.loads(row[0]) if row[0] else [],
                        'include': json.loads(row[1]) if row[1] else []
                    }
                return {'exclude': [], 'include': []}

    async def update_subscription_filters(
            self,
            user_id: int,
            company_name: str,
            exclude_keywords: list = None,
            include_keywords: list = None
    ) -> bool:
        """Обновить фильтры подписки"""
        import json

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                '''UPDATE subscriptions 
                   SET exclude_keywords = ?, include_keywords = ?
                   WHERE user_id = ? AND company_name = ?''',
                (
                    json.dumps(exclude_keywords or [], ensure_ascii=False),
                    json.dumps(include_keywords or [], ensure_ascii=False),
                    user_id,
                    company_name
                )
            )
            await db.commit()
            return cursor.rowcount > 0

    async def is_news_sent(self, user_id: int, news_url: str) -> bool:
        """Проверить, была ли отправлена новость"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                    'SELECT 1 FROM sent_news WHERE user_id = ? AND news_url = ?',
                    (user_id, news_url)
            ) as cursor:
                result = await cursor.fetchone()
                return result is not None

    async def mark_news_as_sent(self, user_id: int, news_url: str) -> bool:
        """Отметить новость как отправленную"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    'INSERT INTO sent_news (user_id, news_url) VALUES (?, ?)',
                    (user_id, news_url)
                )
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def cleanup_old_news(self, days: int = 7):
        """Удалить старые записи об отправленных новостях"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM sent_news WHERE sent_at < datetime('now', '-' || ? || ' days')",
                (days,)
            )
            await db.commit()
