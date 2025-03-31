import pytest
from DbManager.RedisDbManager import RedisDbManager
from Database.main_db import ShortUrl
from datetime import datetime, timezone
import json


@pytest.fixture
def sample_short_url():
    return ShortUrl(
        shortUrl="abc123",
        longUrl="https://example.com",
        timesVisited=5,
        createdAt=datetime(2024, 1, 1, tzinfo=timezone.utc),
        lastVisited=datetime(2024, 1, 2, tzinfo=timezone.utc),
        expiresAt=datetime(2025, 1, 1, tzinfo=timezone.utc)
    )


def test_save_sets_serialized_data(mocker, sample_short_url):
    mock_redis = mocker.Mock()
    mocker.patch("DbManager.RedisDbManager.get_redis_client", return_value=mock_redis)
    redis_manager = RedisDbManager()

    redis_manager.save(sample_short_url)

    mock_redis.set.assert_called_once()
    mock_redis.expire.assert_called_once_with("abc123", redis_manager.LIVE_TIME)

    key, serialized = mock_redis.set.call_args[0]
    assert key == "abc123"

    data = json.loads(serialized)
    assert data["longUrl"] == "https://example.com"
    assert data["timesVisited"] == 5
    assert data["createdAt"].endswith("Z")


def test_get_deserializes_data(mocker):
    mock_redis = mocker.Mock()
    mocker.patch("DbManager.RedisDbManager.get_redis_client", return_value=mock_redis)
    redis_manager = RedisDbManager()

    serialized = json.dumps({
        "shortUrl": "abc123",
        "longUrl": "https://example.com",
        "timesVisited": 5,
        "createdAt": "2024-01-01T00:00:00Z",
        "lastVisited": "2024-01-02T00:00:00Z",
        "expiresAt": "2025-01-01T00:00:00Z"
    })
    mock_redis.get.return_value = serialized

    result = redis_manager.get("abc123")

    assert result is not None
    assert result.shortUrl == "abc123"
    assert result.longUrl == "https://example.com"
    assert result.timesVisited == 5


def test_get_returns_none_if_key_missing(mocker):
    mock_redis = mocker.Mock()
    mocker.patch("Database.redis.get_redis_client", return_value=mock_redis)
    redis_manager = RedisDbManager()

    mock_redis.get.return_value = None
    assert redis_manager.get("not-found") is None


def test_delete_calls_redis(mocker):
    mock_redis = mocker.Mock()
    mocker.patch("DbManager.RedisDbManager.get_redis_client", return_value=mock_redis)
    redis_manager = RedisDbManager()

    redis_manager.delete("abc123")
    mock_redis.delete.assert_called_once_with("abc123")
