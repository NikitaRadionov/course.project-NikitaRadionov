from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_sql_injection_media_filters():
    client.post("/users/", json={"username": "test_sql", "password": "ValidPass123"})
    data = {"username": "test_sql", "password": "ValidPass123"}
    token = client.post("/token", data=data).json()["access_token"]

    response = client.get(
        "/media/?kind=movie' OR '1'='1' --",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code in [400, 422, 404]


def test_rfc7807_format_for_http_exception():

    r = client.get("/media/999", headers={})
    data = r.json()
    assert r.status_code in (401, 404)

    for key in ["type", "title", "status", "detail", "correlation_id"]:
        assert key in data
    assert data["type"] == "about:blank"

    assert "Traceback" not in data["detail"]


def test_validation_invalid_title():

    client.post("/users/", json={"username": "val", "password": "secret"})
    token = client.post(
        "/token",
        data={"username": "val", "password": "secret"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]

    r = client.post(
        "/media/",
        json={"title": "", "kind": "movie", "year": 2000, "status": "planned"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


def test_extra_fields_rejection():
    client.post("/users/", json={"username": "test_extra", "password": "ValidPass123"})
    data = {"username": "test_extra", "password": "ValidPass123"}
    token = client.post("/token", data=data).json()["access_token"]

    response = client.post(
        "/media/",
        json={
            "title": "Valid Title",
            "kind": "movie",
            "year": 2020,
            "status": "planned",
            "injected_field": "malicious_data",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    # Должен отклонить из-за extra='forbid'
    assert response.status_code == 422


def test_password_validation_negative():
    """Негативные тесты валидации пароля"""
    weak_passwords = [
        "short",  # Слишком короткий
        "nouppercase123",  # Без заглавных
        "NOLOWERCASE123",  # Без строчных
        "NoNumbers",  # Без цифр
    ]

    for i, pwd in enumerate(weak_passwords):
        response = client.post(
            "/users/", json={"username": f"test_user_{i}", "password": pwd}
        )
        message = (
            f"Password '{pwd}' should be rejected with 422, got {response.status_code}"
        )
        assert response.status_code == 422, message
