"""Тесты ИИ-ветки BPMN: извлечение, дубликаты, классификация, КП."""

from __future__ import annotations

from app.core.enums import Practice


def _register(client, bot_headers, telegram_id: int, name: str = "ИИ Тест") -> None:
    response = client.post(
        "/api/bot/users",
        headers=bot_headers,
        json={
            "telegram_id": telegram_id,
            "username": f"ai_test_{abs(telegram_id)}",
            "full_name": name,
        },
    )
    assert response.status_code == 200, response.text


def test_ai_intake_fallback_extracts_fields(client, bot_headers):
    _register(client, bot_headers, 700000101, "Иван Петров")
    response = client.post(
        "/api/bot/ai/intake",
        headers=bot_headers,
        json={
            "telegram_id": 700000101,
            "text": (
                "ООО «Вектор», контактное лицо Иван Петров, +7 999 123-45-67, "
                "ivan@example.ru. Нужен финансовый аудит отчётности за 2025 год, "
                "40 часов, сложная задача, бюджет 300 000 руб., срок до 20.12.2026."
            ),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["source"] == "fallback"
    assert data["practice"] == Practice.FINANCE.value
    assert data["hours"] == 40
    assert data["complexity"] == "complex"
    assert data["estimate"]["amount"] == 320000.0
    assert data["company"] and "Вектор" in data["company"]
    assert data["contact_name"] == "Иван Петров"
    assert data["phone"]
    assert data["email"] == "ivan@example.ru"
    assert data["deadline"] == "2026-12-20"
    assert data["kp"]["text"]
    assert data["kp"]["amount"] == 320000.0
    assert data["team"]


def test_ai_intake_finds_duplicate_for_same_client(client, bot_headers):
    telegram_id = 700000102
    _register(client, bot_headers, telegram_id, "Пётр Дублин")
    order = client.post(
        "/api/bot/orders",
        headers=bot_headers,
        json={
            "telegram_id": telegram_id,
            "practice": "finance",
            "title": "Финансовый аудит отчётности за 2025 год",
            "description": "Проверить отчётность, найти ошибки и подготовить рекомендации.",
            "hours": 40,
            "complexity": "complex",
            "client_name": "ООО «Дублин»",
        },
    )
    assert order.status_code == 201, order.text

    response = client.post(
        "/api/bot/ai/intake",
        headers=bot_headers,
        json={
            "telegram_id": telegram_id,
            "text": (
                "Нужен финансовый аудит отчётности за 2025 год, проверить ошибки "
                "и подготовить рекомендации, 40 часов."
            ),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["duplicates"], data
    assert data["duplicates"][0]["number"] == order.json()["number"]
    assert data["duplicates"][0]["similarity"] >= 0.52


def test_create_order_with_ai_kp_document(client, bot_headers):
    telegram_id = 700000103
    _register(client, bot_headers, telegram_id, "КП Тест")
    response = client.post(
        "/api/bot/orders",
        headers=bot_headers,
        json={
            "telegram_id": telegram_id,
            "practice": "management",
            "title": "Стратегическая сессия",
            "description": "Подготовить и провести стратегическую сессию.",
            "hours": 16,
            "complexity": "standard",
            "client_name": "ООО «КП»",
            "kp": {
                "text": "Коммерческое предложение ConsultFlow\nСтоимость: 90 000 ₽",
                "valid_until": "2026-12-01",
                "amount": 90000,
                "sla_hours": 48,
            },
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["number"]

    from app.db.session import SessionLocal
    from app.models import Document

    with SessionLocal() as db:
        document = (
            db.query(Document)
            .filter(Document.order_id == response.json()["id"])
            .one()
        )
        assert document.doc_type == "proposal"
        assert "90 000" in document.payload["body"]
        assert document.payload["meta"]["source"] == "ai"
