"""Интеграция Telegram-бота и API."""

from urllib.parse import parse_qs, urlparse

CLIENT_TG = 555000111
PORTAL_TG = 555000222


def test_duplicate_order_from_bot_is_not_created_twice(client, bot_headers):
    client.post(
        "/api/bot/users",
        headers=bot_headers,
        json={"telegram_id": PORTAL_TG, "full_name": "Клиент Кабинета"},
    )
    payload = {
        "telegram_id": PORTAL_TG,
        "practice": "finance",
        "title": "Повторная заявка из бота",
        "description": "Нужно проверить, что двойное нажатие не создаёт дубль",
        "hours": 8,
        "complexity": "basic",
    }
    first = client.post("/api/bot/orders", headers=bot_headers, json=payload)
    second = client.post("/api/bot/orders", headers=bot_headers, json=payload)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]


def test_client_link_opens_personal_portal(client, bot_headers):
    client.post(
        "/api/bot/users",
        headers=bot_headers,
        json={"telegram_id": PORTAL_TG, "full_name": "Клиент Кабинета"},
    )
    created = client.post(
        "/api/bot/orders",
        headers=bot_headers,
        json={
            "telegram_id": PORTAL_TG,
            "practice": "legal",
            "title": "Заявка для личного кабинета",
            "description": "Проверка персональной ссылки",
            "hours": 12,
            "complexity": "standard",
        },
    )
    assert created.status_code == 201, created.text

    link = client.post(
        "/api/bot/client-link",
        headers=bot_headers,
        json={"telegram_id": PORTAL_TG},
    )
    assert link.status_code == 200, link.text
    token = parse_qs(urlparse(link.json()["url"]).query)["token"][0]

    portal = client.get("/api/client/portal", params={"token": token})
    assert portal.status_code == 200, portal.text
    payload = portal.json()
    assert payload["client_name"] == "Клиент Кабинета"
    numbers = [item["number"] for item in payload["orders"]]
    assert created.json()["number"] in numbers
    assert all(item.startswith("CF-") for item in numbers)

    invalid = client.get("/api/client/portal", params={"token": "invalid-token"})
    assert invalid.status_code == 401



def test_bot_token_required(client):
    assert client.get("/api/bot/health").status_code == 401
    assert (
        client.get("/api/bot/health", headers={"X-Bot-Token": "wrong"}).status_code == 401
    )
    assert (
        client.get("/api/bot/health", headers={"X-Bot-Token": "test-bot-token"}).status_code
        == 200
    )


def test_register_client(client, bot_headers):
    response = client.post(
        "/api/bot/users",
        headers=bot_headers,
        json={
            "telegram_id": CLIENT_TG,
            "username": "integration_client",
            "full_name": "Интеграционный Клиент",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["is_manager"] is False
    assert payload["user"]["role"] == "client"


def test_register_manager(client, bot_headers):
    response = client.post(
        "/api/bot/users",
        headers=bot_headers,
        json={"telegram_id": 700000002, "full_name": "Петров Пётр"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["is_manager"] is True
    assert payload["user"]["role"] == "manager"
    assert payload["user"]["user_id"] is not None


def test_create_order_from_bot(client, bot_headers):
    response = client.post(
        "/api/bot/orders",
        headers=bot_headers,
        json={
            "telegram_id": CLIENT_TG,
            "practice": "it",
            "title": "Заявка из интеграционного теста",
            "description": "Нужен аудит инфраструктуры",
            "hours": 24,
            "complexity": "standard",
            "client_name": "ООО «Тестовый клиент»",
            "phone": "+7 (999) 000-00-00",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["number"].startswith("CF-")
    assert payload["status"] == "new"
    assert payload["practice_label"] == "IT-консалтинг"
    # 6000 ₽/час * 24 ч * 1.25
    assert payload["amount"] == 180000
    assert payload["estimate"]["sla_hours"] == 48
    assert payload["sla_due_at"] is not None


def test_client_sees_own_orders(client, bot_headers):
    response = client.get(
        "/api/bot/orders", headers=bot_headers, params={"telegram_id": CLIENT_TG}
    )
    assert response.status_code == 200
    numbers = [item["number"] for item in response.json()]
    assert numbers
    detail = client.get(
        f"/api/bot/orders/{numbers[0]}",
        headers=bot_headers,
        params={"telegram_id": CLIENT_TG},
    )
    assert detail.status_code == 200
    assert detail.json()["events"]


def test_client_cannot_read_foreign_order(client, bot_headers, admin_headers):
    orders = client.get("/api/orders?page_size=50", headers=admin_headers).json()["items"]
    foreign = next(
        item for item in orders if item["client"]["telegram_id"] != CLIENT_TG
    )
    response = client.get(
        f"/api/bot/orders/{foreign['number']}",
        headers=bot_headers,
        params={"telegram_id": CLIENT_TG},
    )
    assert response.status_code == 403


def test_manager_queue_and_status(client, bot_headers):
    queue = client.get("/api/bot/queue", headers=bot_headers, params={"telegram_id": 700000002})
    assert queue.status_code == 200
    items = queue.json()
    assert items
    target = next(item for item in items if item["status"] == "new")

    changed = client.post(
        f"/api/bot/orders/{target['id']}/status",
        headers=bot_headers,
        json={
            "telegram_id": 700000002,
            "status": "qualified",
            "comment": "Проверено менеджером в боте",
        },
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["status"] == "qualified"

    forbidden = client.post(
        f"/api/bot/orders/{target['id']}/status",
        headers=bot_headers,
        json={"telegram_id": CLIENT_TG, "status": "closed"},
    )
    assert forbidden.status_code == 403


def test_client_forbidden_manager_actions(client, bot_headers):
    assert (
        client.get("/api/bot/queue", headers=bot_headers, params={"telegram_id": CLIENT_TG}).status_code
        == 403
    )
    assert (
        client.get("/api/bot/stats", headers=bot_headers, params={"telegram_id": CLIENT_TG}).status_code
        == 403
    )
    assert (
        client.post("/api/bot/link", headers=bot_headers, json={"telegram_id": CLIENT_TG}).status_code
        == 403
    )


def test_manager_stats_and_link(client, bot_headers):
    stats = client.get("/api/bot/stats", headers=bot_headers, params={"telegram_id": 700000002})
    assert stats.status_code == 200
    payload = stats.json()
    assert payload["orders_total"] >= 72
    assert payload["new_orders"] >= 0

    link = client.post("/api/bot/link", headers=bot_headers, json={"telegram_id": 700000002})
    assert link.status_code == 200
    assert "/magic?token=" in link.json()["url"]
    assert link.json()["expires_in_minutes"] > 0


def test_notifications_outbox(client, bot_headers):
    pending = client.get("/api/bot/notifications", headers=bot_headers)
    assert pending.status_code == 200
    items = pending.json()
    assert items, "Должно быть уведомление менеджеру о новой заявке"
    assert any("Новая заявка" in item["text"] for item in items)

    ack = client.post(
        "/api/bot/notifications/ack",
        headers=bot_headers,
        json={"ids": [item["id"] for item in items]},
    )
    assert ack.status_code == 200
    assert ack.json()["updated"] == len(items)

    after = client.get("/api/bot/notifications", headers=bot_headers).json()
    assert all(item["id"] not in {i["id"] for i in items} for item in after)


def test_bot_pricing(client, bot_headers):
    response = client.get("/api/bot/pricing", headers=bot_headers)
    assert response.status_code == 200
    rates = {item["value"]: item["rate"] for item in response.json()["practices"]}
    assert rates["it"] == 6000
