import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx import ASGITransport
from main import app
from unittest.mock import MagicMock
from Database.redis import get_redis_client
from sqlalchemy.orm import Session
from Database.main_db import SessionLocal
@pytest.fixture
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def mock_redis(mocker):
    mock_client = MagicMock()
    mocker.patch("Database.redis.get_redis_client", return_value=mock_client)
    return mock_client