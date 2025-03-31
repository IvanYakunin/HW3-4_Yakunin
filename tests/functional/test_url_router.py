import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta, timezone
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_urls():
    from Database.main_db import SessionLocal, ShortUrl
    db = SessionLocal()
    db.query(ShortUrl).delete()
    db.commit()
    db.close()


def test_create_short_url_anonymous():
    response = client.post("/links/shorten", json={"url": "https://example.com"})
    assert response.status_code == 200
    assert "url" in response.json()

def test_create_with_invalid_alias():
    # alias больше 7 символов
    long_alias = "thisislong"
    resp = client.post("/links/shorten", json={
        "url": "https://alias-test.com",
        "alias": long_alias
    })
    assert resp.status_code == 422

    # alias с недопустимыми символами
    bad_alias = "bad-alias!"
    resp = client.post("/links/shorten", json={
        "url": "https://alias-test.com",
        "alias": bad_alias
    })
    assert resp.status_code == 422


def test_create_short_url_with_expiration():
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    response = client.post("/links/shorten", json={"url": "https://example.com", "expiresAt": future})
    assert response.status_code == 200
    assert "url" in response.json()


def test_search_by_original_url():
    target_url = "https://find-me.com"
    create_resp = client.post("/links/shorten", json={"url": target_url})
    assert create_resp.status_code == 200

    resp = client.get("/links/search", params={"original_url": target_url})
    assert resp.status_code == 200
    assert "url" in resp.json()


def test_redirect_by_short_url():
    create_resp = client.post("/links/shorten", json={"url": "https://redirect.com"})
    short_code = create_resp.json()["url"]

    resp = client.get(f"/links/{short_code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://redirect.com"

def test_redirect_nonexistent_short_url():
    resp = client.get("/links/doesnotexist", follow_redirects=False)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Short URL not found"


def test_get_url_stats():
    create_resp = client.post("/links/shorten", json={"url": "https://stats.com"})
    short_code = create_resp.json()["url"]

    resp = client.get(f"/links/{short_code}/stats")
    assert resp.status_code == 200
    assert resp.json()["originalUrl"] == "https://stats.com"


def test_delete_url_unauthorized():
    create_resp = client.post("/links/shorten", json={"url": "https://delete-me.com"})
    short_code = create_resp.json()["url"]

    resp = client.delete(f"/links/{short_code}")
    assert resp.status_code == 200
    assert resp.json()["url"] == "Deleted"


def test_update_url_unauthorized():
    create_resp = client.post("/links/shorten", json={"url": "https://old-url.com"})
    short_code = create_resp.json()["url"]

    resp = client.put(f"/links/{short_code}", json={"newUrl": "https://new-url.com"})
    assert resp.status_code == 200
    assert resp.json()["url"] == "https://new-url.com"


def test_dump_database():
    resp = client.get("/admin/dump-db")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_dump_expired_database():
    resp = client.get("/admin/dump-expired")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
