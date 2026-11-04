"""Юнит-тесты расчёта стоимости."""

from app.services.pricing import estimate, get_sla_hours


def test_estimate_it_standard():
    result = estimate("it", 10, "standard")
    assert result["rate"] == 6000
    assert result["multiplier"] == 1.25
    assert result["amount"] == 75000
    assert result["sla_hours"] == 48


def test_estimate_complex_multiplier():
    result = estimate("legal", 10, "complex")
    assert result["amount"] == 88000  # 5500 * 10 * 1.6


def test_estimate_minimum_hours():
    result = estimate("management", 0, "basic")
    assert result["amount"] == 4500


def test_sla_defaults():
    assert get_sla_hours("finance") == 24
    assert get_sla_hours("unknown") == 48
