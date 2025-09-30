import pytest
from fastapi.testclient import TestClient

from app.main import app, create_db_and_tables

client = TestClient(app)


@pytest.fixture(autouse=True, scope="module")
def setup_db():
    create_db_and_tables()
    yield


def register_user(username: str, password: str = "secret"):
    return client.post("/users/", json={"username": username, "password": password})


def login_user(username: str, password: str = "secret"):
    r = client.post(
        "/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200
    return r.json()["access_token"]


def test_create_and_get_media():
    register_user("bob")
    token = login_user("bob")

    r = client.post(
        "/media/",
        json={"title": "Inception", "kind": "movie", "year": 2010, "status": "planned"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    media = r.json()
    assert media["title"] == "Inception"
    media_id = media["id"]

    r2 = client.get(f"/media/{media_id}", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200
    assert r2.json()["id"] == media_id


def test_update_and_delete_media():
    register_user("charlie")
    token = login_user("charlie")

    r = client.post(
        "/media/",
        json={"title": "Matrix", "kind": "movie", "year": 1999, "status": "planned"},
        headers={"Authorization": f"Bearer {token}"},
    )
    media_id = r.json()["id"]

    r2 = client.put(
        f"/media/{media_id}",
        json={
            "title": "Matrix Reloaded",
            "kind": "movie",
            "year": 2003,
            "status": "done",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["title"] == "Matrix Reloaded"

    r3 = client.delete(
        f"/media/{media_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert r3.status_code == 200
    assert r3.json() == {"ok": True}

    r4 = client.get(f"/media/{media_id}", headers={"Authorization": f"Bearer {token}"})
    assert r4.status_code == 404
