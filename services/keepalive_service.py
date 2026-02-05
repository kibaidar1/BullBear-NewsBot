"""Сервис для предотвращения засыпания на Render"""
import logging
from aiohttp import web
from typing import Optional
import aiohttp

logger = logging.getLogger(__name__)


class KeepAliveService:
    """Сервис для поддержания активности бота на Render"""

    def __init__(self, port: int = 8080, external_url: Optional[str] = None):
        self.port = port
        self.external_url = external_url
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self._setup_routes()

    def _setup_routes(self):
        """Настройка маршрутов для health check"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/', self.root)
        self.app.router.add_get('/status', self.status)

    async def health_check(self, request):
        """Endpoint для health check от Render"""
        return web.json_response({
            'status': 'ok',
            'service': 'StockPulse News Bot',
            'uptime': 'running'
        })

    async def root(self, request):
        """Корневой endpoint"""
        return web.json_response({
            'bot': 'StockPulse News Bot',
            'status': 'active',
            'message': 'Bot is running successfully'
        })

    async def status(self, request):
        """Детальный статус бота"""
        return web.json_response({
            'bot': 'StockPulse News Bot',
            'version': '1.0.0',
            'status': 'operational',
            'features': [
                'News monitoring',
                'Company subscriptions',
                'Smart filtering',
                'Scheduled updates'
            ]
        })

    async def start(self):
        """Запустить веб-сервер"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()

        logger.info(f"Keep-alive server started on port {self.port}")

    async def stop(self):
        """Остановить веб-сервер"""
        if self.runner:
            await self.runner.cleanup()
            logger.info("Keep-alive server stopped")

    async def self_ping(self):
        """Пингуем сам себя чтобы не заснуть"""
        if not self.external_url:
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        f"{self.external_url}/health",
                        timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        logger.debug("Self-ping successful")
                    else:
                        logger.warning(f"Self-ping returned status {response.status}")
        except Exception as e:
            logger.error(f"Self-ping failed: {e}")
