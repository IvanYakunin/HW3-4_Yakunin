# tests/unit/test_url_service.py

import pytest
from service.UrlService import UrlService
from DataClasses.DataClasses import CreateShortUrlDC, UpdateUrlDC, ShortUrlStatsDC
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

url_service = UrlService()

def test_create_alias_generates_unique_value(mocker):
    mock_db = MagicMock()
    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=None)
    alias = url_service.create_alias(mock_db)
    assert isinstance(alias, str)
    assert len(alias) > 0

def test_make_short_url_sets_default_expiry_for_anon(mocker):
    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=None)
    mocker.patch.object(url_service.db_manager, "save", return_value=None)
    mocker.patch.object(url_service.redis_manager, "save", return_value=None)

    create_dto = CreateShortUrlDC(url="https://example.com")
    result = url_service.make_short_url(create_dto, user=None)
    assert result.url

def test_make_short_url_honors_custom_expiry_for_anon(mocker):
    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=None)
    mocker.patch.object(url_service.db_manager, "save", return_value=None)
    mocker.patch.object(url_service.redis_manager, "save", return_value=None)

    custom_exp = datetime.now(timezone.utc) + timedelta(hours=24)
    dto = CreateShortUrlDC(url="https://example.com", expiresAt=custom_exp)
    result = url_service.make_short_url(dto, user=None)
    assert result.url

def test_delete_expired_removes_correct_entries(mocker):
    mocker.patch.object(url_service.db_manager, "delete_all_expired", return_value=["a", "b"])
    mocker.patch.object(url_service.db_manager, "delete_unused_for_days", return_value=["c"])
    redis_delete = mocker.patch.object(url_service.redis_manager, "delete", return_value=None)

    url_service.delete_expired(unused_days=5)

    redis_delete.assert_any_call("a")
    redis_delete.assert_any_call("b")
    redis_delete.assert_any_call("c")

@pytest.mark.asyncio
async def test_update_usage_stats_async(mocker):
    mock_entry = MagicMock()
    mock_entry.timesVisited = 0
    mock_entry.lastVisited = None

    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=mock_entry)
    mocker.patch.object(url_service.redis_manager, "save", return_value=None)

    await url_service._update_usage_stats("abc123")

    assert mock_entry.timesVisited == 1
    assert mock_entry.lastVisited is not None

def test_get_short_url_stats_returns_dto(mocker):
    mock_entry = MagicMock()
    mock_entry.longUrl = "https://example.com"
    mock_entry.timesVisited = 10
    mock_entry.lastVisited = datetime.now(timezone.utc)
    mock_entry.createdAt = datetime.now(timezone.utc)

    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=mock_entry)

    stats = url_service.get_short_url_stats("abc123")
    assert isinstance(stats, ShortUrlStatsDC)
    assert stats.originalUrl == "https://example.com"

def test_update_long_url_success(mocker):
    mock_entry = MagicMock()
    mock_entry.owner_id = 1

    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=mock_entry)
    mocker.patch.object(url_service.db_manager, "update_short_url", return_value=mock_entry)
    mocker.patch.object(url_service.redis_manager, "save", return_value=None)

    user = MagicMock()
    user.id = 1
    success = url_service.update_long_url("alias123", "https://new.com", user)
    assert success is True

def test_update_long_url_forbidden(mocker):
    mock_entry = MagicMock()
    mock_entry.owner_id = 2

    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=mock_entry)

    user = MagicMock()
    user.id = 1

    with pytest.raises(HTTPException) as exc:
        url_service.update_long_url("alias123", "https://new.com", user)

    assert exc.value.status_code == 403

def test_delete_by_short_url_owner(mocker):
    mock_entry = MagicMock()
    mock_entry.owner_id = 5

    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=mock_entry)
    mocker.patch.object(url_service.db_manager, "delete_short_url", return_value=mock_entry)
    mocker.patch.object(url_service.redis_manager, "delete", return_value=None)

    user = MagicMock()
    user.id = 5
    success = url_service.delete_by_short_url("alias123", user)
    assert success is True

def test_delete_by_short_url_forbidden(mocker):
    mock_entry = MagicMock()
    mock_entry.owner_id = 99

    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=mock_entry)

    user = MagicMock()
    user.id = 1

    with pytest.raises(HTTPException) as exc:
        url_service.delete_by_short_url("alias123", user)

    assert exc.value.status_code == 403

def test_find_by_original_url_found(mocker):
    mock_entry = MagicMock()
    mock_entry.shortUrl = "abc123"

    mocker.patch.object(url_service.db_manager, "get_by_long_url", return_value=mock_entry)

    result = url_service.find_by_original_url("https://example.com")
    assert result.url == "abc123"

def test_find_by_original_url_not_found(mocker):
    mocker.patch.object(url_service.db_manager, "get_by_long_url", return_value=None)

    with pytest.raises(HTTPException) as exc:
        url_service.find_by_original_url("https://missing.com")

    assert exc.value.status_code == 404

def test_get_short_url_from_db_if_not_cached(mocker):
    mock_short_url = MagicMock()
    mock_short_url.longUrl = "https://from-db.com"
    mock_short_url.timesVisited = 0
    mock_short_url.lastVisited = None

    mocker.patch.object(url_service.redis_manager, "get", return_value=None)
    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=mock_short_url)
    mocker.patch.object(url_service.redis_manager, "save", return_value=None)
    mocker.patch("sqlalchemy.orm.session.Session.commit", return_value=None)

    long_url = url_service.get_short_url("alias123")
    assert long_url == "https://from-db.com"


def test_get_full_url_from_db_if_not_cached(mocker):
    mock_entry = MagicMock()
    mock_entry.longUrl = "https://cached.com"

    mocker.patch.object(url_service.redis_manager, "get", return_value=None)
    mocker.patch.object(url_service.db_manager, "get_by_short_url", return_value=mock_entry)
    mocker.patch.object(url_service.redis_manager, "save", return_value=None)
    mocker.patch("asyncio.create_task", return_value=None)

    url = url_service.get_full_url("abc123")
    assert url == "https://cached.com"


def test_get_all_urls_returns_list(mocker):
    fake_entry = MagicMock()
    fake_entry.id = 1
    fake_entry.shortUrl = "abc"
    fake_entry.longUrl = "https://a.com"
    fake_entry.timesVisited = 1
    fake_entry.createdAt = datetime.now(timezone.utc)
    fake_entry.lastVisited = datetime.now(timezone.utc)
    fake_entry.expiresAt = None

    mock_query = MagicMock()
    mock_query.all.return_value = [fake_entry]
    mocker.patch("sqlalchemy.orm.Session.query", return_value=mock_query)

    mocker.patch("asyncio.create_task", return_value=None)
    result = url_service.get_all_urls()
    assert isinstance(result, list)
    assert result[0]["shortUrl"] == "abc"


def test_get_all_expired_urls_returns_list(mocker):
    fake_entry = MagicMock()
    fake_entry.id = 1
    fake_entry.shortUrl = "expired1"
    fake_entry.longUrl = "https://expired.com"
    fake_entry.timesVisited = 0
    fake_entry.createdAt = datetime.now(timezone.utc)
    fake_entry.lastVisited = None
    fake_entry.expiresAt = datetime.now(timezone.utc)
    fake_entry.deletedAt = datetime.now(timezone.utc)
    fake_entry.owner_id = None

    mocker.patch("sqlalchemy.orm.Session.query", return_value=MagicMock(all=lambda: [fake_entry]))

    result = url_service.get_all_expired_urls()
    assert isinstance(result, list)
    assert result[0]["shortUrl"] == "expired1"
