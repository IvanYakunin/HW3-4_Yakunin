import asyncio
from service.UrlService import UrlService

url_service = UrlService()

async def periodic_expired_cleanup(interval_seconds: int = 3600, unused_days: int = 10):
    """
    Периодически очищает устаревшие ссылки.
    :param interval_seconds: Интервал между проверками в секундах (по умолчанию 1 час)
    """
    while True:
        print("[Cleaner] Checking for expired URLs...")
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: url_service.delete_expired(unused_days))
        await asyncio.sleep(interval_seconds)  # <-- Добавляем это