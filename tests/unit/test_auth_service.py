import pytest
from service.AuthService import AuthService
from DataClasses.DataClasses import UserCreateDC
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from Database.main_db import Base, User
from jose import jwt
from datetime import timedelta, datetime, timezone
from fastapi import HTTPException


# ======= Базовые фикстуры =======

@pytest.fixture
def mock_redis(mocker):
    mock_redis = mocker.Mock()
    mocker.patch("service.AuthService.get_redis_client", return_value=mock_redis)
    return mock_redis

@pytest.fixture
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
def auth_service(mock_redis):
    return AuthService()


# ======= Тесты хеширования и токенов (уже были) =======

def test_hash_and_verify_password(auth_service):
    raw_password = "super_secret"
    hashed = auth_service.hash_password(raw_password)

    assert hashed != raw_password
    assert auth_service.verify_password(raw_password, hashed)

def test_create_and_decode_token(auth_service):
    data = {"sub": "test@example.com"}
    token = auth_service.create_access_token(data, expires_delta=timedelta(minutes=5))
    decoded = auth_service.decode_token(token)

    assert decoded["sub"] == "test@example.com"
    assert "exp" in decoded
    assert isinstance(decoded["exp"], int)

def test_token_expiration(auth_service):
    data = {"sub": "test@example.com"}
    token = auth_service.create_access_token(data, expires_delta=timedelta(seconds=1))
    auth_service.decode_token(token)
    import time
    time.sleep(2)
    with pytest.raises(jwt.ExpiredSignatureError):
        auth_service.decode_token(token)


# ======= Новые тесты =======

def test_register_and_login_user(auth_service, db_session):
    dto = UserCreateDC(email="test@user.com", password="12345")
    token = auth_service.register_user(dto, db_session)
    assert token.access_token

    # логин с теми же данными
    token2 = auth_service.login_user(dto, db_session)
    assert token2.access_token

def test_register_user_duplicate_email(auth_service, db_session):
    dto = UserCreateDC(email="duplicate@user.com", password="123")
    auth_service.register_user(dto, db_session)

    with pytest.raises(HTTPException) as exc:
        auth_service.register_user(dto, db_session)

    assert exc.value.status_code == 400
    assert "Email already registered" in str(exc.value.detail)

def test_login_user_invalid_password(auth_service, db_session):
    user = User(email="a@b.com", password_hash=auth_service.hash_password("realpass"))
    db_session.add(user)
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        auth_service.login_user(UserCreateDC(email="a@b.com", password="wrongpass"), db_session)

    assert exc.value.status_code == 401

def test_get_current_user_valid(auth_service, db_session):
    user = User(email="valid@user.com", password_hash="hashed")
    db_session.add(user)
    db_session.commit()

    token = auth_service.create_access_token({"sub": user.email})
    user_out = auth_service.get_current_user(token, db_session)

    assert user_out.email == "valid@user.com"

def test_get_current_user_blacklisted(auth_service, db_session, mock_redis):
    mock_redis.exists.return_value = 1  # токен в черном списке

    token = auth_service.create_access_token({"sub": "blocked@user.com"})
    with pytest.raises(HTTPException) as exc:
        auth_service.get_current_user(token, db_session)

    assert exc.value.status_code == 401
    assert "blacklisted" in str(exc.value.detail)

def test_logout_token_adds_to_blacklist(auth_service, mock_redis):
    token = auth_service.create_access_token({"sub": "logout@test.com"}, timedelta(seconds=10))
    auth_service.logout_token(token)

    mock_redis.set.assert_called_once()
    key = mock_redis.set.call_args[0][0]
    assert key.startswith("blacklist:")

def test_is_token_blacklisted_true(auth_service, mock_redis):
    mock_redis.exists.return_value = 1
    assert auth_service.is_token_blacklisted("token") is True

def test_is_token_blacklisted_false(auth_service, mock_redis):
    mock_redis.exists.return_value = 0
    assert auth_service.is_token_blacklisted("token") is False

def test_get_all_users(auth_service, db_session):
    user1 = User(email="user1@ex.com", password_hash="1")
    user2 = User(email="user2@ex.com", password_hash="2")
    db_session.add_all([user1, user2])
    db_session.commit()

    result = auth_service.get_all_users(db_session)
    assert len(result) == 2
    assert result[0]["email"].startswith("user")
