from src.Database.redis import get_redis_client
from src.Database.main_db import ShortUrl
from datetime import datetime, timezone
import json

class RedisDbManager:
    LIVE_TIME = 60 * 60 * 12

    def __init__(self):
        self.redis = get_redis_client()

    def save(self, short_url: ShortUrl):

        def format_dt(dt: datetime | None) -> str | None:
            if not dt:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

        data = {
            "shortUrl": short_url.shortUrl,
            "longUrl": short_url.longUrl,
            "timesVisited": short_url.timesVisited,
            "createdAt": format_dt(short_url.createdAt),
            "lastVisited": format_dt(short_url.lastVisited),
            "expiresAt": format_dt(short_url.expiresAt)
        }
        serialized = json.dumps(data)
        self.redis.set(short_url.shortUrl, serialized)
        self.redis.expire(short_url.shortUrl, self.LIVE_TIME)

    def get(self, short_url: str):
        serialized = self.redis.get(short_url)
        if not serialized:
            return None
        
        data = json.loads(serialized)
        
        # Создание объекта ShortUrl
        def parse_dt(iso_str: str | None) -> datetime | None:
            if not iso_str:
                return None
            if iso_str.endswith("Z"):
                iso_str = iso_str.replace("Z", "+00:00")
            return datetime.fromisoformat(iso_str).astimezone(timezone.utc)

        return ShortUrl(
            shortUrl=data["shortUrl"],
            longUrl=data["longUrl"],
            timesVisited=data["timesVisited"],
            createdAt=parse_dt(data["createdAt"]),
            lastVisited=parse_dt(data["lastVisited"]),
            expiresAt=parse_dt(data["expiresAt"])
        )
    
    def delete(self, short_url: str):
        self.redis.delete(short_url)