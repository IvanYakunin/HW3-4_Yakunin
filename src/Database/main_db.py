from sqlalchemy import create_engine, Column, Integer, String, DateTime, func, Boolean, ForeignKey
from datetime import datetime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Настройка подключения
engine = create_engine('sqlite:///urls.db', echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ShortUrl(Base):
    __tablename__ = 'urls'
    
    id = Column(Integer, primary_key=True, index=True)
    shortUrl = Column(String, name="short_url", nullable=False, unique=True)
    longUrl = Column(String, name="long_url", nullable=False)
    timesVisited = Column(Integer, name="times_visited", default=0, nullable=False)
    createdAt = Column(DateTime, name="created_at", server_default=func.now(), nullable=False)
    lastVisited = Column(DateTime, name="last_visited", server_default=func.now(), nullable=False)
    expiresAt = Column(DateTime, name="expires_at", nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", backref="urls")

    def __init__(
        self,
        shortUrl: str,
        longUrl: str,
        timesVisited: int = 0,
        createdAt: datetime | None = None,
        lastVisited: datetime | None = None,
        expiresAt: datetime | None = None,
        owner_id: Integer | None = None
    ):
        self.shortUrl = shortUrl
        self.longUrl = longUrl
        self.timesVisited = timesVisited
        self.createdAt = createdAt
        self.lastVisited = lastVisited
        self.expiresAt = expiresAt
        self.owner_id = owner_id


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())


class ExpiredUrl(Base):
    __tablename__ = "expired_urls"

    id = Column(Integer, primary_key=True, index=True)
    shortUrl = Column(String, nullable=False)
    longUrl = Column(String, nullable=False)
    timesVisited = Column(Integer, default=0, nullable=False)
    createdAt = Column(DateTime, nullable=False)
    lastVisited = Column(DateTime, nullable=True)
    expiresAt = Column(DateTime, nullable=True)
    deletedAt = Column(DateTime, default=func.now(), nullable=False)
    owner_id = Column(Integer, nullable=True)


Base.metadata.create_all(engine)