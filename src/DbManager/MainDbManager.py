from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from Database.main_db import ShortUrl, ExpiredUrl
from fastapi import HTTPException
from datetime import datetime, timezone, timedelta
from sqlalchemy import and_

class MainDbManager:

    def save(self, shortUrl: ShortUrl, db: Session):
        existing = db.query(ShortUrl).filter(ShortUrl.shortUrl == shortUrl.shortUrl).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Alias '{shortUrl.shortUrl}' already exists"
            )
        
        try:
            db.add(shortUrl)
            db.commit()
            db.refresh(shortUrl)
            return shortUrl
        except IntegrityError:
            db.rollback()
            return None

    def update_short_url(self, short_url: str, new_full_url: str, db: Session):
        db_entry = db.query(ShortUrl).filter(ShortUrl.shortUrl == short_url).first()

        if db_entry:
            db_entry.longUrl = new_full_url
            db.commit()
            db.refresh(db_entry)
            return db_entry
        else:
            return None

    def delete_short_url(self, short_url: str, db: Session):
        db_entry = db.query(ShortUrl).filter(ShortUrl.shortUrl == short_url).first()
        if db_entry:
            self.move_to_expired(db_entry, db)  # Архивируем перед удалением
            db.delete(db_entry)
            db.commit()
            return db_entry
        return None

    def get_by_short_url(self, short_url: str, db: Session):
        return db.query(ShortUrl).filter(ShortUrl.shortUrl == short_url).first()

    def delete_all_expired(self, db: Session) -> list[str]:
        curr_time = datetime.now(timezone.utc)
        expired = db.query(ShortUrl).filter(
            and_(ShortUrl.expiresAt.isnot(None), ShortUrl.expiresAt <= curr_time)
        ).all()

        deleted_aliases = []
        for entry in expired:
            self.move_to_expired(entry, db)
            deleted_aliases.append(entry.shortUrl)
            db.delete(entry)

        db.commit()
        return deleted_aliases


    def delete_unused_for_days(self, db: Session, days: int = 10) -> list[str]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        unused = db.query(ShortUrl).filter(ShortUrl.lastVisited <= cutoff).all()

        deleted_aliases = []
        for entry in unused:
            self.move_to_expired(entry, db)
            deleted_aliases.append(entry.shortUrl)
            db.delete(entry)

        db.commit()
        return deleted_aliases

    def get_by_long_url(self, long_url: str, db: Session):
        return db.query(ShortUrl).filter(ShortUrl.longUrl == long_url).first()
    
    def move_to_expired(self, entry: ShortUrl, db: Session):
        archived = ExpiredUrl(
            shortUrl=entry.shortUrl,
            longUrl=entry.longUrl,
            timesVisited=entry.timesVisited,
            createdAt=entry.createdAt,
            lastVisited=entry.lastVisited,
            expiresAt=entry.expiresAt,
            owner_id=entry.owner_id
        )
        db.add(archived)
    