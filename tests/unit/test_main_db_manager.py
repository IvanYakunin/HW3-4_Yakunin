import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from Database.main_db import Base, ShortUrl, ExpiredUrl
from DbManager.MainDbManager import MainDbManager
from datetime import datetime, timedelta, timezone

# Настройка in-memory SQLite
@pytest.fixture(scope="function")
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def manager():
    return MainDbManager()

def test_save_and_get(manager, db_session):
    entry = ShortUrl(shortUrl="abc", longUrl="https://test.com")
    saved = manager.save(entry, db_session)
    assert saved.id is not None

    fetched = manager.get_by_short_url("abc", db_session)
    assert fetched.longUrl == "https://test.com"

def test_save_conflict(manager, db_session):
    entry = ShortUrl(shortUrl="abc", longUrl="https://test.com")
    manager.save(entry, db_session)

    with pytest.raises(Exception):
        manager.save(ShortUrl(shortUrl="abc", longUrl="https://other.com"), db_session)

def test_update_short_url(manager, db_session):
    entry = ShortUrl(shortUrl="abc", longUrl="https://old.com")
    manager.save(entry, db_session)

    updated = manager.update_short_url("abc", "https://new.com", db_session)
    assert updated.longUrl == "https://new.com"

def test_delete_short_url_and_archive(manager, db_session):
    entry = ShortUrl(shortUrl="abc", longUrl="https://delete.com")
    manager.save(entry, db_session)

    deleted = manager.delete_short_url("abc", db_session)
    assert deleted.shortUrl == "abc"

    archived = db_session.query(ExpiredUrl).filter_by(shortUrl="abc").first()
    assert archived is not None
    assert archived.longUrl == "https://delete.com"

def test_get_by_long_url(manager, db_session):
    entry = ShortUrl(shortUrl="xyz", longUrl="https://long.com")
    manager.save(entry, db_session)

    found = manager.get_by_long_url("https://long.com", db_session)
    assert found.shortUrl == "xyz"

def test_delete_all_expired(manager, db_session):
    expired = ShortUrl(
        shortUrl="exp1",
        longUrl="https://exp.com",
        expiresAt=datetime.now(timezone.utc) - timedelta(days=1)
    )
    active = ShortUrl(
        shortUrl="active",
        longUrl="https://active.com",
        expiresAt=datetime.now(timezone.utc) + timedelta(days=2)
    )
    db_session.add_all([expired, active])
    db_session.commit()

    deleted = manager.delete_all_expired(db_session)
    assert "exp1" in deleted
    assert "active" not in deleted

def test_delete_unused_for_days(manager, db_session):
    unused = ShortUrl(
        shortUrl="old1",
        longUrl="https://old.com",
        lastVisited=datetime.now(timezone.utc) - timedelta(days=20)
    )
    fresh = ShortUrl(
        shortUrl="new1",
        longUrl="https://new.com",
        lastVisited=datetime.now(timezone.utc)
    )
    db_session.add_all([unused, fresh])
    db_session.commit()

    deleted = manager.delete_unused_for_days(db_session, days=10)
    assert "old1" in deleted
    assert "new1" not in deleted

def test_move_to_expired_creates_entry(manager, db_session):
    url = ShortUrl(shortUrl="toarchive", longUrl="https://archive.com")
    db_session.add(url)
    db_session.commit()

    manager.move_to_expired(url, db_session)
    archived = db_session.query(ExpiredUrl).filter_by(shortUrl="toarchive").first()
    assert archived is not None
