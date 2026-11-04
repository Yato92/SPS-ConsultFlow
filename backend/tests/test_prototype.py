"""Интеграция учебного прототипа с API и базой данных."""


def _create(client, email: str = "proto-test@example.ru") -> dict:
    response = client.post(
        "/api/prototype/orders",
        json={
            "company": "ООО «Прототип-Тест»",
            "contact": "Тестовый Клиент",
            "email": email,
            "description": "Нужна консультация по развитию процесса продаж",
            "file_name": "brief.pdf",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_database_health(client):
    response = client.get("/health/db")
    assert response.status_code == 200, response.text
    assert response.json()["dialect"] == "sqlite"


def test_bootstrap_returns_demo_orders_and_dictionaries(client):
    response = client.get("/api/prototype/bootstrap")
    assert response.status_code == 200, response.text
    payload = response.json()
    numbers = {item["number"] for item in payload["orders"]}
    assert {"101", "102", "103", "104"} <= numbers
    demo = next(item for item in payload["orders"] if item["number"] == "104")
    assert demo["company"] == "ООО «Вектор»"
    assert demo["contact"] == "Иван Петров"
    assert demo["manager"] == "Алексей Иванов"
    assert demo["proposalVersion"] == 0
    assert demo["history"]
    assert payload["current"]["id"] == payload["orders"][0]["id"]
    assert {item["value"] for item in payload["practices"]} == {
        "management",
        "finance",
        "legal",
        "it",
    }
    assert "Анна Смирнова" in payload["consultants"]


def test_full_prototype_lifecycle(client):
    created = _create(client, "lifecycle@example.ru")
    order_id = created["id"]
    assert created["status"] == "new"
    assert created["file"] == "brief.pdf"

    clarified = client.post(
        f"/api/prototype/orders/{order_id}/clarify",
        json={"question": "Сколько сотрудников участвует в процессе?"},
    )
    assert clarified.status_code == 200, clarified.text
    assert clarified.json()["status"] == "clarification"
    assert clarified.json()["clarification"].startswith("Сколько")

    answered = client.post(
        f"/api/prototype/orders/{order_id}/answer",
        json={"answer": "Двенадцать сотрудников"},
    )
    assert answered.status_code == 200
    assert answered.json()["answer"] == "Двенадцать сотрудников"

    proposal = client.post(
        f"/api/prototype/orders/{order_id}/proposal",
        json={
            "solution": "Диагностика процесса и план оптимизации.",
            "cost": 55000,
            "days": 7,
            "sla": "Ответ в течение 1 рабочего дня",
            "consultant": "Дмитрий Орлов",
        },
    )
    assert proposal.status_code == 200, proposal.text
    assert proposal.json()["status"] == "sent"
    assert proposal.json()["proposalVersion"] == 1
    assert proposal.json()["cost"] == 55000
    assert any(doc["type"] == "proposal" for doc in proposal.json()["documents"])

    signed = client.post(f"/api/prototype/orders/{order_id}/sign")
    assert signed.status_code == 200, signed.text
    assert signed.json()["signed"] is True

    declined = client.post(
        f"/api/prototype/orders/{order_id}/pay",
        json={
            "card_number": "4000 0000 0000 0002",
            "holder": "TEST CLIENT",
            "expiry": "12/40",
            "cvc": "123",
        },
    )
    assert declined.status_code == 400
    assert "отклонил" in declined.json()["detail"]

    payment = client.post(
        f"/api/prototype/orders/{order_id}/pay",
        json={
            "card_number": "4111 1111 1111 1111",
            "holder": "TEST CLIENT",
            "expiry": "12/40",
            "cvc": "123",
        },
    )
    assert payment.status_code == 200, payment.text
    assert payment.json()["paid"] is True
    assert payment.json()["paymentLast4"] == "1111"
    assert any(doc["type"] == "payment" for doc in payment.json()["documents"])
    assert any("Тестовая оплата" in item["text"] for item in payment.json()["history"])

    duplicate_payment = client.post(
        f"/api/prototype/orders/{order_id}/pay",
        json={
            "card_number": "4111 1111 1111 1111",
            "holder": "TEST CLIENT",
            "expiry": "12/40",
            "cvc": "123",
        },
    )
    assert duplicate_payment.status_code == 400
    assert "уже оплачена" in duplicate_payment.json()["detail"]

    contract = client.post(f"/api/prototype/orders/{order_id}/contract")
    assert contract.status_code == 200, contract.text
    assert contract.json()["contract"] is True
    assert any(doc["type"] == "contract" for doc in contract.json()["documents"])

    started = client.post(f"/api/prototype/orders/{order_id}/start")
    assert started.status_code == 200
    assert started.json()["status"] == "in_progress"
    assert started.json()["workStarted"] is True

    act = client.post(f"/api/prototype/orders/{order_id}/act")
    assert act.status_code == 200
    assert act.json()["act"] is True

    confirmed = client.post(f"/api/prototype/orders/{order_id}/confirm-act")
    assert confirmed.status_code == 200, confirmed.text
    payload = confirmed.json()
    assert payload["status"] == "done"
    assert payload["actConfirmed"] is True
    assert any("Акт подтверждён" in item["text"] for item in payload["history"])

    current = client.get(f"/api/prototype/bootstrap?order_id={order_id}").json()
    assert current["current"]["id"] == order_id


def test_remarks_create_revision_and_second_proposal(client):
    created = _create(client, "remarks@example.ru")
    order_id = created["id"]
    proposal = client.post(
        f"/api/prototype/orders/{order_id}/proposal",
        json={
            "solution": "Первая версия решения.",
            "cost": 30000,
            "days": 5,
            "sla": "Ответ в течение 1 рабочего дня",
            "consultant": "Анна Смирнова",
        },
    )
    assert proposal.status_code == 200

    remarks = client.post(
        f"/api/prototype/orders/{order_id}/remarks",
        json={"text": "Добавьте обучение сотрудников в состав работ"},
    )
    assert remarks.status_code == 200, remarks.text
    assert remarks.json()["status"] == "revision"
    assert "обучение" in remarks.json()["remarks"]

    second = client.post(
        f"/api/prototype/orders/{order_id}/proposal",
        json={
            "solution": "Вторая версия решения с обучением сотрудников.",
            "cost": 40000,
            "days": 6,
            "sla": "Ответ в течение 1 рабочего дня",
            "consultant": "Анна Смирнова",
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["status"] == "sent"
    assert second.json()["proposalVersion"] == 2
    assert second.json()["remarks"] is None
    assert len([doc for doc in second.json()["documents"] if doc["type"] == "proposal"]) == 2


def test_invalid_action_returns_bad_request(client):
    created = _create(client, "invalid@example.ru")
    order_id = created["id"]
    signed = client.post(f"/api/prototype/orders/{order_id}/sign")
    assert signed.status_code == 400
    assert "КП" in signed.json()["detail"]

    contract = client.post(f"/api/prototype/orders/{order_id}/contract")
    assert contract.status_code == 400

    payment = client.post(
        f"/api/prototype/orders/{order_id}/pay",
        json={
            "card_number": "4111 1111 1111 1111",
            "holder": "TEST CLIENT",
            "expiry": "12/40",
            "cvc": "123",
        },
    )
    assert payment.status_code == 400
    assert "КП" in payment.json()["detail"]


def test_seed_idempotent(client):
    from app.db.session import SessionLocal
    from app.seed import seed, seed_prototype

    with SessionLocal() as db:
        assert seed(db) is False
        assert seed_prototype(db) is False
        count = client.get("/api/prototype/orders").json()
    assert len(count) >= 4
