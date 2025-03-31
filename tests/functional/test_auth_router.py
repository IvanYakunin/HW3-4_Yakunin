import pytest
from fastapi.testclient import TestClient
from main import app
from service.AuthService import AuthService
from Database.main_db import SessionLocal, User

client = TestClient(app)
auth_service = AuthService()

@pytest.fixture(autouse=True)
def clear_users():
    db = SessionLocal()
    db.query(User).delete()
    db.commit()
    db.close()

def test_register_and_login():
    email = "user@example.com"
    password = "secure123"

    # Регистрация
    response = client.post("/auth/register", json={
        "email": email,
        "password": password
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    assert token

    # Логин
    response = client.post("/auth/login", data={
        "username": email,
        "password": password
    })
    assert response.status_code == 200
    login_token = response.json()["access_token"]
    assert login_token

def test_check_token_valid_and_invalid():
    email = "valid@example.com"
    password = "pass123"

    # Регистрация
    reg_resp = client.post("/auth/register", json={"email": email, "password": password})
    token = reg_resp.json()["access_token"]

    # Проверка валидного токена
    response = client.get("/auth/check-token", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["valid"] is True

    # Проверка невалидного токена
    response = client.get("/auth/check-token", headers={"Authorization": "Bearer fake.token"})
    assert response.status_code == 200
    assert response.json()["valid"] is False

def test_logout_and_blacklist():
    email = "logout@example.com"
    password = "pass123"

    reg_resp = client.post("/auth/register", json={"email": email, "password": password})
    token = reg_resp.json()["access_token"]

    # logout
    response = client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["detail"] == "Successfully logged out"

    # token теперь невалидный
    response = client.get("/auth/check-token", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["valid"] is False

def test_get_all_users():
    # Создаём пользователя
    client.post("/auth/register", json={"email": "admin@example.com", "password": "admin123"})

    # Запрашиваем всех пользователей
    response = client.get("/auth/admin/users")
    assert response.status_code == 200
    users = response.json()
    assert isinstance(users, list)
    assert len(users) >= 1
