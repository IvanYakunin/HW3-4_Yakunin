import base64
import uuid
import asyncio
import random
import string
from datetime import datetime, timezone, timedelta
from fastapi.exceptions import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.DataClasses.DataClasses import LongUrlDC, CreateShortUrlDC, ShortUrlDC, ShortUrlStatsDC
from src.Database.main_db import SessionLocal, User, ExpiredUrl
from src.DbManager.MainDbManager import MainDbManager, ShortUrl
from src.DbManager.RedisDbManager import RedisDbManager

VALID_ALIAS_CHARS = string.ascii_letters + string.digits + "_"


class UrlService:
    def __init__(self):
        self.db_manager = MainDbManager()
        self.redis_manager = RedisDbManager()

    def make_short_url(self, create_short_info: CreateShortUrlDC, user: User | None = None) -> ShortUrlDC:
        db = SessionLocal()
        try:
            alias = create_short_info.alias or self.create_alias(db)

            # Если пользователь не авторизован — устанавливаем макс время жизни 12 часов
            expires_at = create_short_info.expiresAt
            if not user:
                if expires_at:
                    expires_at = min(datetime.now(timezone.utc) + timedelta(hours=12), expires_at)
                else:
                    expires_at = datetime.now(timezone.utc) + timedelta(hours=12)


            short_url = ShortUrl(
                shortUrl=alias,
                longUrl=create_short_info.url,
                expiresAt=expires_at,
                owner_id=user.id if user else None
            )

            self.db_manager.save(shortUrl=short_url, db=db)
            self.redis_manager.save(short_url=short_url)

            return ShortUrlDC(url=alias)
        finally:
            db.close()

    def create_alias(self, db: Session) -> str:
        while True:
            raw_alias = ''.join(random.choices(VALID_ALIAS_CHARS, k=6))
            exists = self.db_manager.get_by_short_url(raw_alias, db)
            if not exists:
                return raw_alias

    def get_short_url(self, alias: str) -> str:
        db = SessionLocal()
        try:
            short_url = self.redis_manager.get(alias)
            if not short_url:
                short_url = self.db_manager.get_by_short_url(alias, db)
                if not short_url:
                    raise HTTPException(status_code=404, detail="Short URL not found")
                self.redis_manager.save(short_url)

            short_url.timesVisited += 1
            short_url.lastVisited = datetime.now(timezone.utc)
            db.commit()

            self.redis_manager.save(short_url)

            return short_url.longUrl
        finally:
            db.close()

    def get_short_url_stats(self, alias: str) -> ShortUrlStatsDC:
        db = SessionLocal()
        try:
            short_url = self.db_manager.get_by_short_url(alias, db)
            if not short_url:
                raise HTTPException(status_code=404, detail="Short URL not found")

            return ShortUrlStatsDC(
                originalUrl=short_url.longUrl,
                visits=short_url.timesVisited,
                lastTimeUsed=short_url.lastVisited,
                createdAt=short_url.createdAt
            )
        finally:
            db.close()

    def delete_by_short_url(self, alias: str, user: User | None = None) -> bool:
        db = SessionLocal()
        try:
            entry = self.db_manager.get_by_short_url(alias, db)
            if not entry:
                return False
            if entry.owner_id and entry.owner_id != user.id:
                raise HTTPException(status_code=403, detail="Not your link")
            deleted = self.db_manager.delete_short_url(alias, db)
            self.redis_manager.delete(alias)
            return deleted is not None
        finally:
            db.close()

    def get_by_long_url(self, long_url: str, db: Session):
        return db.query(ShortUrl).filter(ShortUrl.longUrl == long_url).first()
    
    def update_long_url(self, alias: str, new_url: str, user: User | None = None) -> bool:
        db = SessionLocal()
        try:
            entry = self.db_manager.get_by_short_url(alias, db)
            if not entry:
                raise HTTPException(status_code=404, detail="Short URL not found")

            if entry.owner_id and (not user or entry.owner_id != user.id):
                raise HTTPException(status_code=403, detail="You are not the owner of this link")

            updated = self.db_manager.update_short_url(alias, new_url, db)
            if updated:
                self.redis_manager.save(updated)
                return True
            return False
        finally:
            db.close()

    def delete_expired(self, unused_days: int = 10):
        db = SessionLocal()
        try:
            expired_aliases = self.db_manager.delete_all_expired(db)
            unused_aliases = self.db_manager.delete_unused_for_days(db=db, days=unused_days)

            # Очистка кэша
            for alias in expired_aliases + unused_aliases:
                self.redis_manager.delete(alias)
        finally:
            db.close()

    def get_full_url(self, alias: str) -> str:
        short_url = self.redis_manager.get(alias)

        if not short_url:
            # Попытка достать из БД и кэшировать
            db = SessionLocal()
            try:
                short_url = self.db_manager.get_by_short_url(alias, db)
                if not short_url:
                    raise HTTPException(status_code=404, detail="Short URL not found")
                self.redis_manager.save(short_url)
            finally:
                db.close()

        # Если нашли — запускаем фоновую задачу
        asyncio.create_task(self._update_usage_stats(alias))

        return short_url.longUrl
    
    async def _update_usage_stats(self, alias: str):
        def sync_update():
            db = SessionLocal()
            try:
                entry = self.db_manager.get_by_short_url(alias, db)
                if entry:
                    entry.timesVisited += 1
                    entry.lastVisited = datetime.now(timezone.utc)
                    db.commit()
                    self.redis_manager.save(entry)
            finally:
                db.close()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, sync_update)

    def find_by_original_url(self, url: str) -> ShortUrlDC:
        db = SessionLocal()
        print('===========================')
        print(url)
        try:
            entry = self.db_manager.get_by_long_url(url, db)
            if not entry:
                raise HTTPException(status_code=404, detail="Not found")
            return ShortUrlDC(url=entry.shortUrl)
        finally:
            db.close()


    def get_all_urls(self) -> list[dict]:
        db = SessionLocal()
        try:
            entries = db.query(ShortUrl).all()
            return [
                {
                    "id": e.id,
                    "shortUrl": e.shortUrl,
                    "longUrl": e.longUrl,
                    "visits": e.timesVisited,
                    "createdAt": e.createdAt,
                    "lastVisited": e.lastVisited,
                    "expiresAt": e.expiresAt
                }
                for e in entries
            ]
        finally:
            db.close()


    def get_all_expired_urls(self) -> list[dict]:
        db = SessionLocal()
        try:
            entries = db.query(ExpiredUrl).all()
            return [
                {
                    "id": e.id,
                    "shortUrl": e.shortUrl,
                    "longUrl": e.longUrl,
                    "visits": e.timesVisited,
                    "createdAt": e.createdAt,
                    "lastVisited": e.lastVisited,
                    "expiresAt": e.expiresAt,
                    "deletedAt": e.deletedAt,
                    "owner_id": e.owner_id
                }
                for e in entries
            ]
        finally:
            db.close()
