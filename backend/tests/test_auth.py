"""Авторизация, JWT и magic-link."""

import jwt
import pytest


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_login_success_and_me(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@consultflow.ru", "password": "admin12345"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert payload["user"]["role"] == "admin"

    me = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {payload['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "admin@consultflow.ru"


def test_login_wrong_password(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@consultflow.ru", "password": "wrong-pass"},
    )
    assert response.status_code == 401


def test_requires_token(client):
    assert client.get("/api/orders").status_code == 401
    assert client.get("/api/dashboard").status_code == 401


def test_magic_link_flow(client, bot_headers):
    link = client.post("/api/bot/link", headers=bot_headers, json={"telegram_id": 700000002})
    assert link.status_code == 200
    url = link.json()["url"]
    token = url.split("token=", 1)[1]

    response = client.post("/api/auth/magic", json={"token": token})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "manager"


def test_magic_link_rejects_access_token(client, admin_headers):
    token = admin_headers["Authorization"].split(" ", 1)[1]
    response = client.post("/api/auth/magic", json={"token": token})
    assert response.status_code == 401


def test_magic_link_rejects_broken_token(client):
    response = client.post("/api/auth/magic", json={"token": "broken.token.value"})
    assert response.status_code == 401

    with pytest.raises(jwt.PyJWTError):
        jwt.decode("broken.token.value", "secret", algorithms=["HS256"])
