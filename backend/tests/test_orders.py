"""CRUD заказов, статусы и документы."""

from datetime import date, timedelta


def _first_client(client, headers) -> dict:
    response = client.get("/api/clients?limit=1", headers=headers)
    assert response.status_code == 200
    return response.json()["items"][0]


def test_list_and_filters(client, admin_headers):
    response = client.get("/api/orders?page_size=5", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 72
    assert len(payload["items"]) == 5
    assert payload["items"][0]["client"]["name"]

    it_only = client.get("/api/orders?practice=it&page_size=100", headers=admin_headers)
    assert it_only.status_code == 200
    assert all(item["practice"] == "it" for item in it_only.json()["items"])

    statuses = client.get(
        "/api/orders?status=new,qualified&page_size=100", headers=admin_headers
    )
    assert all(item["status"] in {"new", "qualified"} for item in statuses.json()["items"])


def test_search_by_number(client, admin_headers):
    order = client.get("/api/orders?page_size=1", headers=admin_headers).json()["items"][0]
    found = client.get(
        f"/api/orders?q={order['number']}", headers=admin_headers
    )
    assert found.status_code == 200
    assert found.json()["total"] >= 1
    assert found.json()["items"][0]["number"] == order["number"]


def test_create_order_and_lifecycle(client, manager_headers):
    client_row = _first_client(client, manager_headers)
    payload = {
        "client_id": client_row["id"],
        "practice": "it",
        "title": "Тестовый проект внедрения BI",
        "description": "Проверка создания заказа через API",
        "amount": 250000,
        "deadline": (date.today() + timedelta(days=30)).isoformat(),
    }
    created = client.post("/api/orders", json=payload, headers=manager_headers)
    assert created.status_code == 201, created.text
    order = created.json()
    assert order["number"].startswith("CF-")
    assert order["status"] == "new"
    assert order["amount"] == 250000
    assert order["manager"] is not None

    order_id = order["id"]
    detail = client.get(f"/api/orders/{order_id}", headers=manager_headers)
    assert detail.status_code == 200
    assert len(detail.json()["events"]) == 1
    assert detail.json()["events"][0]["to_status"] == "new"

    # Новый -> Квалифицирован -> КП отправлено
    step = client.post(
        f"/api/orders/{order_id}/status",
        json={"status": "qualified", "comment": "Данные полные"},
        headers=manager_headers,
    )
    assert step.status_code == 200, step.text
    assert step.json()["status"] == "qualified"

    # Недопустимый переход blocked
    invalid = client.post(
        f"/api/orders/{order_id}/status",
        json={"status": "closed"},
        headers=manager_headers,
    )
    assert invalid.status_code == 400

    proposal = client.post(
        f"/api/orders/{order_id}/status",
        json={"status": "proposal"},
        headers=manager_headers,
    )
    assert proposal.status_code == 200
    docs = proposal.json()["documents"]
    assert any(doc["doc_type"] == "proposal" for doc in docs)
    proposal_doc = next(doc for doc in docs if doc["doc_type"] == "proposal")
    assert proposal_doc["number"].startswith("КП-")
    assert "Коммерческое предложение" in proposal_doc["payload"]["title"]

    signed = client.post(
        f"/api/orders/{order_id}/documents/{proposal_doc['id']}/sign",
        headers=manager_headers,
    )
    assert signed.status_code == 200
    assert signed.json()["status"] == "signed"


def test_update_amounts(client, manager_headers):
    order = client.get("/api/orders?page_size=1", headers=manager_headers).json()["items"][0]
    response = client.patch(
        f"/api/orders/{order['id']}",
        json={"paid_amount": 100000, "expenses": 40000, "description": "Обновлено"},
        headers=manager_headers,
    )
    assert response.status_code == 200
    assert response.json()["paid_amount"] == 100000
    assert response.json()["expenses"] == 40000


def test_consultant_cannot_create_order(client, admin_headers):
    login = client.post(
        "/api/auth/login",
        json={"email": "consultant@consultflow.ru", "password": "consultant12345"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    client_row = _first_client(client, admin_headers)
    response = client.post(
        "/api/orders",
        json={
            "client_id": client_row["id"],
            "practice": "it",
            "title": "Запрещённая операция",
            "amount": 1000,
        },
        headers=headers,
    )
    assert response.status_code == 403


def test_export_csv(client, manager_headers):
    response = client.get("/api/orders/export/csv", headers=manager_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "Номер" in response.text
    assert "CF-" in response.text


def test_admin_can_force_status(client, admin_headers):
    order = client.get("/api/orders?page_size=1", headers=admin_headers).json()["items"][0]
    if order["status"] == "closed":
        return
    response = client.post(
        f"/api/orders/{order['id']}/status",
        json={"status": "closed", "comment": "Принудительное закрытие"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "closed"


def test_soft_delete_hides_order_but_keeps_in_database(client, manager_headers):
    client_row = _first_client(client, manager_headers)
    created = client.post(
        "/api/orders",
        json={
            "client_id": client_row["id"],
            "practice": "legal",
            "title": "Заказ для проверки мягкого удаления",
            "amount": 15000,
        },
        headers=manager_headers,
    )
    assert created.status_code == 201, created.text
    order_id = created.json()["id"]
    number = created.json()["number"]

    deleted = client.delete(f"/api/orders/{order_id}", headers=manager_headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["is_deleted"] is True

    # В обычном списке заявки больше нет.
    visible = client.get(
        f"/api/orders?q={number}", headers=manager_headers
    ).json()
    assert visible["total"] == 0
    assert client.get(f"/api/orders/{order_id}", headers=manager_headers).status_code == 404

    # Но запись осталась в базе: её видно в архиве.
    archived = client.get(
        "/api/orders?include_deleted=true", headers=manager_headers
    ).json()
    archived_order = next(
        (item for item in archived["items"] if item["id"] == order_id), None
    )
    assert archived_order is not None
    assert archived_order["is_deleted"] is True

    restored = client.post(f"/api/orders/{order_id}/restore", headers=manager_headers)
    assert restored.status_code == 200, restored.text
    assert restored.json()["is_deleted"] is False
    visible_again = client.get(f"/api/orders?q={number}", headers=manager_headers).json()
    assert visible_again["total"] == 1
