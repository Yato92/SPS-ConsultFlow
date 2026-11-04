"""Общие фикстуры тестов ConsultFlow."""

import os
from pathlib import Path

import pytest

TEST_DIR = Path(__file__).resolve().parent
DB_PATH = TEST_DIR / "consultflow_test.db"

if DB_PATH.exists():
    DB_PATH.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH.as_posix()}"
os.environ["SEED_DEMO"] = "true"
os.environ["BOT_API_TOKEN"] = "test-bot-token"
os.environ["MANAGER_TELEGRAM_IDS"] = "700000002"
os.environ["SECRET_KEY"] = "test-secret-key-at-least-32-bytes-long"
os.environ["ADMIN_EMAIL"] = "admin@consultflow.ru"
os.environ["ADMIN_PASSWORD"] = "admin12345"


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def admin_headers(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@consultflow.ru", "password": "admin12345"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def manager_headers(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "manager@consultflow.ru", "password": "manager12345"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def bot_headers():
    return {"X-Bot-Token": "test-bot-token"}
