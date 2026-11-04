"""Клавиатуры VK-бота (JSON-кнопки сообщества)."""

from __future__ import annotations

import json

COLOR = "primary"
SECONDARY = "secondary"
NEGATIVE = "negative"


def _button(label: str, color: str = SECONDARY) -> dict:
    return {
        "action": {"type": "text", "label": label[:40]},
        "color": color,
    }


def _keyboard(rows: list[list[dict]], *, one_time: bool = False) -> str:
    return json.dumps(
        {
            "one_time": one_time,
            "inline": False,
            "buttons": rows,
        },
        ensure_ascii=False,
    )


def main_menu(is_manager: bool = False) -> str:
    rows: list[list[dict]] = [
        [_button("📝 Оставить заявку", COLOR)],
        [_button("✨ AI-заявка", COLOR)],
        [_button("📋 Мои заявки"), _button("🤖 Спросить ИИ")],
        [_button("💰 Прайс-лист"), _button("🖥 Кабинет")],
    ]
    if is_manager:
        rows.insert(1, [_button("📥 Очередь заявок", COLOR)])
        rows.insert(4, [_button("🖥 Дашборд")])
    rows.append([_button("❓ Помощь")])
    return _keyboard(rows)


def ai_confirm() -> str:
    return _keyboard(
        [
            [_button("✅ Создать заявку", COLOR)],
            [_button("Отмена", NEGATIVE)],
        ],
        one_time=True,
    )


def practices() -> str:
    return _keyboard(
        [
            [_button("Управленческий", COLOR), _button("Финансовый", COLOR)],
            [_button("Юридический", COLOR), _button("IT-консалтинг", COLOR)],
            [_button("Отмена", NEGATIVE)],
        ],
        one_time=True,
    )


def hours() -> str:
    return _keyboard(
        [
            [_button("8 ч"), _button("16 ч"), _button("24 ч")],
            [_button("40 ч"), _button("80 ч")],
            [_button("Отмена", NEGATIVE)],
        ],
        one_time=True,
    )


def complexity() -> str:
    return _keyboard(
        [
            [_button("Базовая", COLOR)],
            [_button("Стандартная", COLOR)],
            [_button("Сложная", COLOR)],
            [_button("Отмена", NEGATIVE)],
        ],
        one_time=True,
    )


def confirm() -> str:
    return _keyboard(
        [[_button("Подтвердить", COLOR)], [_button("Отмена", NEGATIVE)]],
        one_time=True,
    )


def back() -> str:
    return _keyboard([[_button("🏠 Главное меню")]])
