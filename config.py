"""Конфигурация бота"""
import os
from dataclasses import dataclass
from environs import Env


@dataclass
class TgBot:
    """Конфигурация Telegram бота"""
    token: str


@dataclass
class GNewsConfig:
    """Конфигурация GNews API"""
    api_key: str
    base_url: str = "https://gnews.io/api/v4/search"
    language: str = "ru"
    max_results: int = 5


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    path: str


@dataclass
class SchedulerConfig:
    """Конфигурация планировщика"""
    check_interval: int  # в секундах


@dataclass
class RenderConfig:
    """Конфигурация для Render"""
    port: int
    external_url: str | None
    is_render: bool


@dataclass
class Config:
    """Главная конфигурация"""
    tg_bot: TgBot
    gnews: GNewsConfig
    database: DatabaseConfig
    scheduler: SchedulerConfig
    render: RenderConfig


def load_config(path: str = None) -> Config:
    """Загрузка конфигурации из .env файла"""
    env = Env()
    env.read_env(path)

    # Проверяем, запущены ли мы на Render
    is_render = os.getenv('RENDER') == 'true' or os.getenv('RENDER_EXTERNAL_URL') is not None

    # Путь к БД зависит от окружения
    default_db_path = 'news_bot.db'
    if is_render:
        # На Render используем примонтированный диск
        os.makedirs('/opt/render/project/src/data', exist_ok=True)
        default_db_path = '/opt/render/project/src/data/news_bot.db'

    return Config(
        tg_bot=TgBot(
            token=env.str("BOT_TOKEN")
        ),
        gnews=GNewsConfig(
            api_key=env.str("GNEWS_API_KEY"),
            language=env.str("GNEWS_LANGUAGE", "ru"),
            max_results=env.int("GNEWS_MAX_RESULTS", 5)
        ),
        database=DatabaseConfig(
            path=env.str("DATABASE_PATH", default_db_path)
        ),
        scheduler=SchedulerConfig(
            check_interval=env.int("CHECK_INTERVAL", 3600)
        ),
        render=RenderConfig(
            port=env.int("PORT", 8080),
            external_url=env.str("RENDER_EXTERNAL_URL", None),
            is_render=is_render
        )
    )
