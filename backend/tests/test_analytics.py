"""Проверка агрегатов дашборда."""

from datetime import date


def test_dashboard_shape(client, admin_headers):
    response = client.get("/api/dashboard", headers=admin_headers)
    assert response.status_code == 200
    payload = response.json()

    summary = payload["summary"]
    assert summary["orders_total"] >= 72
    assert summary["active_orders"] > 0
    assert len(payload["monthly"]) == 12
    assert len(payload["by_practice"]) == 4
    assert payload["by_status"]
    assert payload["recent_orders"]
    assert "generated_at" in payload


def test_dashboard_totals_match_orders(client, admin_headers):
    dashboard = client.get("/api/dashboard", headers=admin_headers).json()
    orders = client.get("/api/orders?page_size=200", headers=admin_headers).json()

    paid = sum(item["paid_amount"] for item in orders["items"])
    expenses = sum(item["expenses"] for item in orders["items"])
    amount = sum(item["amount"] for item in orders["items"])

    assert dashboard["summary"]["orders_total"] == orders["total"]
    assert round(dashboard["summary"]["paid_total"], 2) == round(paid, 2)
    assert round(dashboard["summary"]["expenses_total"], 2) == round(expenses, 2)
    assert round(dashboard["summary"]["amount_total"], 2) == round(amount, 2)
    assert round(dashboard["summary"]["profit"], 2) == round(paid - expenses, 2)


def test_by_practice_sums_to_total(client, admin_headers):
    dashboard = client.get("/api/dashboard", headers=admin_headers).json()
    paid_by_practice = sum(item["paid"] for item in dashboard["by_practice"])
    assert round(paid_by_practice, 2) == round(dashboard["summary"]["paid_total"], 2)


def test_date_filter(client, admin_headers):
    all_data = client.get("/api/dashboard", headers=admin_headers).json()
    narrow = client.get(
        "/api/dashboard",
        params={"date_from": date.today().isoformat()},
        headers=admin_headers,
    ).json()
    assert narrow["summary"]["orders_total"] <= all_data["summary"]["orders_total"]
    assert all(
        point["orders"] >= 0 for point in narrow["monthly"]
    )


def test_pricing_endpoint(client, admin_headers):
    response = client.get("/api/dashboard/pricing", headers=admin_headers)
    assert response.status_code == 200
    assert len(response.json()["practices"]) == 4
