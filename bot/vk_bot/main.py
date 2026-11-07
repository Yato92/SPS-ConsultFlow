"""VK-бот ConsultFlow: Long Poll, заявки, статусы и ИИ-консультант."""

from __future__ import annotations

import asyncio
import html
import logging
import os
import re
from collections import deque
from pathlib import Path
from typing import Any

if os.name == "nt":
    import msvcrt
else:
    import fcntl

from consultflow_bot.ai import AIError, PolzaClient, build_system_prompt, split_message
from consultflow_bot.api import APIError, ConsultFlowAPI
from consultflow_bot.config import get_settings
from consultflow_bot.utils import money
from vk_bot import keyboards
from vk_bot.api import VKAPI, VKError

logger = logging.getLogger(__name__)

PRACTICES = {
    "управленческий": ("management", "Управленческий консалтинг"),
    "финансовый": ("finance", "Финансовый консалтинг"),
    "юридический": ("legal", "Юридический консалтинг"),
    "it-консалтинг": ("it", "IT-консалтинг"),
    "ит-консалтинг": ("it", "IT-консалтинг"),
}
COMPLEXITY = {
    "базовая": ("basic", "Базовая ×1.0"),
    "стандартная": ("standard", "Стандартная ×1.25"),
    "сложная": ("complex", "Сложная ×1.6"),
}

_profiles: dict[int, dict[str, Any]] = {}
_sessions: dict[int, dict[str, Any]] = {}
_histories: dict[int, deque[dict[str, str]]] = {}
_seen_messages: deque[tuple[int, int]] = deque(maxlen=2000)
_seen_message_set: set[tuple[int, int]] = set()
_lock_handle: Any = None


def acquire_instance_lock() -> None:
    """Не дать запустить второй VK-бот: иначе он дублирует сообщения и заявки."""
    global _lock_handle
    lock_path = Path(__file__).resolve().parents[2] / ".vk_bot.lock"
    try:
        _lock_handle = lock_path.open("a+b")
        _lock_handle.seek(0, os.SEEK_END)
        if _lock_handle.tell() == 0:
            _lock_handle.write(b" ")
            _lock_handle.flush()
        _lock_handle.seek(0)
        if os.name == "nt":
            msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(_lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        logger.error(
            "VK-бот уже запущен в другом окне. Закройте его и запустите один экземпляр."
        )
        raise SystemExit(1) from None


def _is_duplicate_message(message: dict[str, Any]) -> bool:
    """VK иногда повторяет событие после переподключения Long Poll."""
    try:
        key = (int(message.get("from_id") or 0), int(message.get("id") or 0))
    except (TypeError, ValueError):
        return False
    if key[1] <= 0:
        return False
    if key in _seen_message_set:
        return True
    if len(_seen_messages) == _seen_messages.maxlen:
        oldest = _seen_messages[0]
        _seen_message_set.discard(oldest)
    _seen_messages.append(key)
    _seen_message_set.add(key)
    return False


def _clean(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text or "")).strip()


def _full_name(user: dict[str, Any]) -> str:
    name = " ".join(
        part for part in (user.get("first_name"), user.get("last_name")) if part
    ).strip()
    return name or "Клиент ВКонтакте"


def _session(user_id: int) -> dict[str, Any]:
    return _sessions.setdefault(user_id, {"step": None, "data": {}})


def _reset(user_id: int) -> None:
    _sessions.pop(user_id, None)


def _history(user_id: int, limit: int) -> deque[dict[str, str]]:
    history = _histories.get(user_id)
    if history is None or history.maxlen != limit:
        history = deque(maxlen=limit)
        _histories[user_id] = history
    return history


async def send(
    vk: VKAPI,
    user_id: int,
    text: str,
    *,
    keyboard: str | None = None,
) -> None:
    chunks = split_message(text, 4000)
    for index, chunk in enumerate(chunks):
        try:
            await vk.send_message(
                user_id,
                chunk,
                keyboard=keyboard if index == len(chunks) - 1 else None,
                dont_parse_links=False,
            )
        except VKError as exc:
            if exc.code != 912 or not keyboard:
                raise
            # У сообщества не включён режим чат-бота: VK не принимает клавиатуру.
            logger.warning("VK chat bot feature is disabled; falling back to text")
            note = (
                "\n\n⚠️ Кнопки пока недоступны. Включите «Чат-бот» "
                "в настройках сообщества, а пока пишите команды текстом."
                if index == 0
                else ""
            )
            await vk.send_message(user_id, chunk + note, dont_parse_links=False)


async def ensure_profile(
    vk: VKAPI, api: ConsultFlowAPI, user_id: int
) -> dict[str, Any] | None:
    if user_id in _profiles:
        return _profiles[user_id]
    try:
        user = await vk.get_user(user_id)
    except VKError as exc:
        logger.warning("VK users.get failed for %s: %s", user_id, exc)
        user = {}
    try:
        profile = await api.register(
            -user_id,
            user.get("screen_name"),
            _full_name(user),
        )
    except APIError as exc:
        logger.warning("VK register failed for %s: %s", user_id, exc)
        return None
    profile = {**profile, "vk_name": _full_name(user), "vk_screen": user.get("screen_name")}
    _profiles[user_id] = profile
    return profile


def welcome(profile: dict[str, Any]) -> str:
    name = profile.get("vk_name") or "друг"
    if profile.get("is_manager"):
        return (
            f"👋 {name}, здравствуйте!\n\n"
            "Это ConsultFlow — бот для работы с заявками.\n"
            "Вы вошли как менеджер: можно смотреть очередь, статистику и дашборд, "
            "а также спросить ИИ-консультанта.\n\n"
            "Выберите действие кнопкой ниже или напишите вопрос."
        )
    return (
        f"👋 {name}, здравствуйте!\n\n"
        "Это ConsultFlow — от заявки до акта один процесс.\n"
        "Оставьте заявку на консалтинг: бот рассчитает предварительную стоимость "
        "и срок ответа, а менеджер свяжется с вами.\n\n"
        "Можно выбрать действие кнопкой ниже или просто написать вопрос — "
        "ответит ИИ-консультант."
    )


def help_text(is_manager: bool) -> str:
    if is_manager:
        return (
            "❓ Как работает VK-бот\n\n"
            "• «Очередь заявок» — откройте заявку и смените статус кнопкой.\n"
            "• «Прайс-лист» — ставки и SLA.\n"
            "• «Кабинет» — ваши заявки и документы по персональной ссылке.\n"
            "• Напишите вопрос — ответит ИИ-консультант.\n\n"
            "Команды: /start — меню, /cancel — отмена, /id — ваш VK ID."
        )
    return (
        "❓ Как оставить заявку\n\n"
        "1. Нажмите «Оставить заявку».\n"
        "2. Выберите направление консалтинга.\n"
        "3. Опишите задачу одним сообщением.\n"
        "4. Укажите объём в часах и сложность.\n"
        "5. Подтвердите заявку — бот покажет стоимость и срок ответа.\n\n"
        "✨ «AI-заявка» — опишите задачу свободным текстом: ИИ сам извлечёт "
        "данные, определит практику, проверит дубликаты, оценит стоимость, "
        "подберёт команду и подготовит черновик КП.\n\n"
        "Статус смотрите в «Мои заявки». Нажмите номер заявки — откроется "
        "карточка: там можно прочитать документы, подписать КП, провести "
        "тестовую оплату и подтвердить работу.\n\n"
        "Можно просто написать вопрос — ответит ИИ-консультант.\n\n"
        "Команды: /start — меню, /cancel — отмена, /id — ваш VK ID."
    )


MISSING_LABELS = {
    "hours": "часы",
    "company": "компания",
    "contact_name": "контактное лицо",
    "contact": "телефон или email",
    "deadline": "срок",
    "phone": "телефон",
    "email": "email",
}
RISK_LABELS = {"low": "низкий", "medium": "средний", "high": "высокий"}


def analysis_text(data: dict[str, Any]) -> str:
    estimate = data.get("estimate") or {}
    kp = data.get("kp") or {}
    team = ", ".join(
        f"{item.get('full_name')} ({item.get('role_label')})"
        for item in data.get("team") or []
    ) or "менеджер ConsultFlow"
    lines = [
        "🤖 AI разобрал заявку",
        "",
        f"Направление: {data.get('practice_label')}",
        f"Задача: {data.get('title')}",
        f"Часы: {float(data.get('hours') or 0):g} · {data.get('complexity_label')}",
        f"Стоимость: {money(estimate.get('amount', 0))}",
        f"SLA: {estimate.get('sla_hours')} ч, риск {RISK_LABELS.get(data.get('sla_risk'), data.get('sla_risk'))}",
        f"Команда: {team}",
    ]
    if data.get("company"):
        lines.append(f"Компания: {data['company']}")
    if data.get("contact_name"):
        lines.append(f"Контакт: {data['contact_name']}")
    if data.get("phone"):
        lines.append(f"Телефон: {data['phone']}")
    if data.get("email"):
        lines.append(f"Email: {data['email']}")
    if data.get("deadline"):
        lines.append(f"Срок: {data['deadline']}")
    missing = [
        MISSING_LABELS.get(item, item)
        for item in data.get("missing_fields") or []
    ]
    if missing:
        lines.append(f"Уточнить: {', '.join(missing)}")
    duplicates = data.get("duplicates") or []
    if duplicates:
        lines.extend(["", "⚠️ Похожие заявки:"])
        for item in duplicates[:3]:
            lines.append(
                f"№{item.get('number')} — {item.get('title')} "
                f"({round(float(item.get('similarity', 0)) * 100)}%)"
            )
    else:
        lines.extend(["", "✅ Дубликатов не найдено."])
    lines.extend(["", f"📄 КП: {kp.get('title') or 'черновик подготовлен'}"])
    if kp.get("text"):
        lines.extend(["", kp["text"]])
    lines.extend(["", "Создать заявку с этими данными?"])
    return "\n".join(lines)


async def start_ai_intake(vk: VKAPI, user_id: int) -> None:
    session = _session(user_id)
    session.update(
        {
            "step": "ai_request",
            "data": {},
            "active_order_id": None,
            "client_actions": {},
            "manager_actions": {},
        }
    )
    await send(
        vk,
        user_id,
        "✨ AI-заявка\n\n"
        "Опишите задачу одним сообщением: что нужно сделать, для какой компании, "
        "какие сроки и ориентир по бюджету.\n\n"
        "ИИ сам определит направление, оценит часы и стоимость, подберёт команду, "
        "проверит базу на дубликаты и подготовит черновик КП.",
        keyboard=keyboards.back(),
    )


async def analyze_ai_intake(
    vk: VKAPI,
    api: ConsultFlowAPI,
    user_id: int,
    profile: dict[str, Any],
    text: str,
) -> None:
    await vk.set_typing(user_id)
    try:
        analysis = await api.ai_intake(
            -user_id,
            text,
            client_name=profile.get("vk_name"),
        )
    except APIError as exc:
        await send(
            vk,
            user_id,
            f"⚠️ {exc.message}\n\nПопробуйте описать задачу ещё раз.",
            keyboard=keyboards.back(),
        )
        return

    session = _session(user_id)
    session.update({"step": "ai_confirm", "data": {"analysis": analysis, "text": text}})
    await send(vk, user_id, analysis_text(analysis), keyboard=keyboards.ai_confirm())


def pricing_text(payload: dict[str, Any]) -> str:
    lines = ["💰 Прайс-лист ConsultFlow", "", "Направления:"]
    for item in payload.get("practices", []):
        lines.append(
            f"• {item.get('label', '—')} — {money(item.get('rate', 0))}/час, "
            f"SLA {item.get('sla_hours', '—')} ч"
        )
    lines.extend(["", "Коэффициенты сложности:"])
    for item in payload.get("complexities", []):
        lines.append(
            f"• {item.get('label', '—')} — ×{item.get('multiplier', 1)}"
        )
    lines.extend(
        [
            "",
            "Итоговая стоимость = ставка × часы × коэффициент. "
            "Точную смету подтверждает менеджер.",
        ]
    )
    return "\n".join(lines)


async def show_menu(
    vk: VKAPI, api: ConsultFlowAPI, user_id: int, profile: dict[str, Any]
) -> None:
    _reset(user_id)
    await send(
        vk,
        user_id,
        welcome(profile),
        keyboard=keyboards.main_menu(bool(profile.get("is_manager"))),
    )


async def start_order(vk: VKAPI, user_id: int) -> None:
    session = _session(user_id)
    session.update(
        {
            "step": "practice",
            "data": {},
            "active_order_id": None,
            "client_actions": {},
            "manager_actions": {},
        }
    )
    await send(
        vk,
        user_id,
        "📝 Оставить заявку\n\nВыберите направление консалтинга:",
        keyboard=keyboards.practices(),
    )


async def show_orders(
    vk: VKAPI, api: ConsultFlowAPI, user_id: int, is_manager: bool = False
) -> None:
    try:
        items = await api.my_orders(-user_id, limit=10)
    except APIError as exc:
        await send(vk, user_id, f"⚠️ {exc.message}", keyboard=keyboards.main_menu(is_manager))
        return

    if not items:
        await send(
            vk,
            user_id,
            "📋 У вас пока нет заявок.\nНажмите «Оставить заявку» в меню.",
            keyboard=keyboards.main_menu(is_manager),
        )
        return

    lines = ["📋 Мои заявки", ""]
    for item in items:
        lines.append(
            f"№{item.get('number', '—')} · {item.get('status_label', item.get('status', '—'))}\n"
            f"{item.get('title', '—')}\n"
            f"Сумма: {money(item.get('amount', 0))}\n"
        )
    lines.append("Нажмите номер заявки ниже — откроется карточка с действиями.")
    try:
        link = await api.client_link(-user_id)
        lines.append(f"\n🖥 Личный кабинет на сайте:\n{link['url']}")
    except APIError:
        pass
    numbers = [str(item.get("number")) for item in items if item.get("number")]
    await send(
        vk,
        user_id,
        "\n".join(lines),
        keyboard=keyboards.orders_list(numbers),
    )


async def show_client_cabinet(
    vk: VKAPI, api: ConsultFlowAPI, user_id: int, profile: dict[str, Any]
) -> None:
    """Персональная ссылка в кабинет: клиент видит только свои заявки."""
    try:
        link = await api.client_link(-user_id)
    except APIError as exc:
        await send(
            vk,
            user_id,
            f"⚠️ {exc.message}",
            keyboard=keyboards.main_menu(bool(profile.get("is_manager"))),
        )
        return
    await send(
        vk,
        user_id,
        "🖥 Ваш личный кабинет\n\n"
        "Ссылка действует "
        f"{link['expires_in_minutes'] // 60 // 24} дн. и показывает только ваши заявки:\n"
        f"{link['url']}",
        keyboard=keyboards.main_menu(bool(profile.get("is_manager"))),
    )


async def show_queue(
    vk: VKAPI, api: ConsultFlowAPI, user_id: int
) -> None:
    try:
        items = await api.queue(-user_id)
    except APIError as exc:
        await send(vk, user_id, f"⚠️ {exc.message}", keyboard=keyboards.main_menu())
        return
    if not items:
        await send(
            vk,
            user_id,
            "📥 Очередь пуста — новых заявок нет.",
            keyboard=keyboards.main_menu(),
        )
        return
    lines = ["📥 Очередь заявок", ""]
    for item in items[:10]:
        lines.append(
            f"№{item.get('number', '—')} · {item.get('status_label', '—')}\n"
            f"{item.get('title', '—')}\n"
            f"{money(item.get('amount', 0))}\n"
        )
    lines.append("Нажмите номер заявки ниже, чтобы открыть карточку и сменить статус.")
    numbers = [str(item.get("number")) for item in items if item.get("number")]
    await send(
        vk,
        user_id,
        "\n".join(lines),
        keyboard=keyboards.orders_list(numbers),
    )


async def _find_order_id(
    api: ConsultFlowAPI, user_id: int, number: str
) -> int | None:
    try:
        # Менеджеру /orders отдаёт все заявки, клиенту — только его собственные.
        items = await api.my_orders(-user_id, limit=50)
    except APIError:
        return None
    for item in items:
        if str(item.get("number")) == number:
            return int(item.get("id") or 0) or None
    return None


def card_text(card: dict[str, Any]) -> str:
    lines = [
        f"📄 Заявка №{card.get('number', '—')}",
        f"Статус: {card.get('status_label', card.get('status', '—'))}",
        f"{card.get('title', '—')}",
        "",
        f"Направление: {card.get('practice_label', '—')}",
        f"Сумма: {money(card.get('amount', 0))}",
        f"Оплачено: {money(card.get('paid_amount', 0))}",
    ]
    if card.get("description"):
        lines.extend(["", f"Описание: {card['description']}"])
    documents = card.get("documents") or []
    if documents:
        lines.extend(["", "Документы:"])
        for doc in documents:
            lines.append(f"• {doc.get('label', 'Документ')} — {doc.get('status', '—')}")
    lines.extend(
        [
            "",
            "Выберите действие кнопкой ниже. "
            "«Прочитать документы» покажет текст КП, договора и акта.",
        ]
    )
    return "\n".join(lines)


def documents_text(card: dict[str, Any]) -> str:
    parts = [f"📄 Документы по заявке №{card.get('number', '—')}", ""]
    documents = card.get("documents") or []
    if not documents:
        parts.append("Документы ещё не сформированы.")
        return "\n".join(parts)
    for doc in documents:
        parts.extend(
            [
                f"=== {doc.get('label', 'Документ')} ({doc.get('status', '—')}) ===",
                str(doc.get("body") or "Текст документа пока не готов."),
                "",
            ]
        )
    return "\n".join(parts)


async def show_order_card(
    vk: VKAPI,
    api: ConsultFlowAPI,
    user_id: int,
    profile: dict[str, Any],
    *,
    order_id: int | None = None,
    number: str | None = None,
) -> None:
    """Карточка заявки с кнопками клиента и сотрудника."""
    is_manager = bool(profile.get("is_manager"))
    if order_id is None and number:
        order_id = await _find_order_id(api, user_id, number)
    if order_id is None:
        await send(
            vk,
            user_id,
            "Заявка не найдена. Откройте «Мои заявки» и выберите её из списка.",
            keyboard=keyboards.main_menu(is_manager),
        )
        return
    try:
        card = await api.client_order(order_id, -user_id)
    except APIError as exc:
        await send(vk, user_id, f"⚠️ {exc.message}", keyboard=keyboards.main_menu(is_manager))
        return

    state = _session(user_id)
    state.update(
        {
            "step": None,
            "active_order_id": order_id,
            "active_order": card.get("number"),
            "client_actions": {
                str(item.get("label")): (str(item.get("code")), item.get("value"))
                for item in card.get("actions") or []
            },
            "manager_actions": {
                str(item.get("label")): (str(item.get("code")), item.get("value"))
                for item in card.get("manager_actions") or []
            },
        }
    )
    await send(
        vk,
        user_id,
        card_text(card),
        keyboard=keyboards.order_actions(
            card.get("actions"), card.get("manager_actions")
        ),
    )


async def _reload_card(
    vk: VKAPI, api: ConsultFlowAPI, user_id: int, profile: dict[str, Any]
) -> None:
    state = _session(user_id)
    order_id = state.get("active_order_id")
    if order_id:
        await show_order_card(vk, api, user_id, profile, order_id=int(order_id))
    else:
        await show_orders(vk, api, user_id, bool(profile.get("is_manager")))


async def execute_order_action(
    vk: VKAPI,
    api: ConsultFlowAPI,
    user_id: int,
    profile: dict[str, Any],
    action: str,
    value: str | None = None,
) -> None:
    state = _session(user_id)
    order_id = state.get("active_order_id")
    if not order_id:
        await send(
            vk,
            user_id,
            "Сначала откройте заявку в «Мои заявки».",
            keyboard=keyboards.main_menu(bool(profile.get("is_manager"))),
        )
        return

    is_manager_action = action in {
        code for code, _ in (state.get("manager_actions") or {}).values()
    }
    try:
        if is_manager_action:
            card = await api.manager_action(order_id, -user_id, action, value)
        else:
            card = await api.client_action(order_id, -user_id, action, value)
    except APIError as exc:
        await send(vk, user_id, f"⚠️ {exc.message}")
        await _reload_card(vk, api, user_id, profile)
        return

    success = {
        "answer": "✅ Ответ отправлен сотруднику.",
        "sign": "✅ КП подписано.",
        "remarks": "✍️ Замечания отправлены сотруднику.",
        "pay": "💳 Тестовая оплата прошла. Деньги не списываются.",
        "confirm": "✅ Работа подтверждена, заявка закрыта.",
        "status": "✅ Статус заявки обновлён.",
    }.get(action)
    if success:
        await send(vk, user_id, success)
    await show_order_card(vk, api, user_id, profile, order_id=order_id)


async def handle_client_step(
    vk: VKAPI,
    api: ConsultFlowAPI,
    user_id: int,
    profile: dict[str, Any],
    text: str,
) -> bool:
    """Шаги клиента в VK: ввод текста, подтверждение, кнопки карточки."""
    state = _session(user_id)
    lower = text.lower().strip()
    step = state.get("step")

    if step == "client_text":
        if lower in {"отмена", "/cancel", "cancel", "назад"}:
            state["step"] = None
            state["pending_action"] = None
            state["pending_value"] = None
            await send(vk, user_id, "Ок, действие отменено.")
            await _reload_card(vk, api, user_id, profile)
            return True
        action = str(state.get("pending_action") or "")
        state["step"] = None
        state["pending_action"] = None
        state["pending_value"] = None
        await execute_order_action(vk, api, user_id, profile, action, text)
        return True

    if step == "client_confirm":
        action = str(state.get("pending_action") or "")
        value = state.get("pending_value")
        state["step"] = None
        state["pending_action"] = None
        state["pending_value"] = None
        if lower.startswith(("подтверд", "да", "оплат", "✅")) or lower in {"ok", "ок"}:
            await execute_order_action(vk, api, user_id, profile, action, value)
        else:
            await send(vk, user_id, "Ок, действие отменено.")
            await _reload_card(vk, api, user_id, profile)
        return True

    label = text.strip()
    for source in ("client_actions", "manager_actions"):
        mapping = state.get(source) or {}
        if label in mapping:
            action, value = mapping[label]
            if action in {"answer", "remarks"}:
                state["step"] = "client_text"
                state["pending_action"] = action
                state["pending_value"] = value
                prompt = (
                    "Напишите ответ на уточнение одним сообщением."
                    if action == "answer"
                    else "Опишите замечания к КП одним сообщением."
                )
                await send(vk, user_id, prompt, keyboard=keyboards.back())
                return True
            if action in {"sign", "pay", "confirm", "status"}:
                state["step"] = "client_confirm"
                state["pending_action"] = action
                state["pending_value"] = value
                prompts = {
                    "sign": "Подписать КП?",
                    "pay": "Провести тестовую оплату? Деньги не списываются.",
                    "confirm": "Подтвердить, что работа выполнена?",
                    "status": f"Применить действие «{label}»?",
                }
                await send(
                    vk,
                    user_id,
                    prompts.get(action, "Подтвердить действие?"),
                    keyboard=keyboards.confirm(),
                )
                return True
            if action == "read":
                try:
                    card = await api.client_order(int(state["active_order_id"]), -user_id)
                except APIError as exc:
                    await send(vk, user_id, f"⚠️ {exc.message}")
                    return True
                await send(vk, user_id, documents_text(card))
                await show_order_card(
                    vk, api, user_id, profile, order_id=int(state["active_order_id"])
                )
                return True
            if action == "refresh":
                await _reload_card(vk, api, user_id, profile)
                return True

    if label.startswith("📄 "):
        number = label[2:].strip()
        await show_order_card(vk, api, user_id, profile, number=number)
        return True

    candidate = label.lstrip("№ ").strip()
    if candidate.upper().startswith("CF-"):
        await show_order_card(vk, api, user_id, profile, number=candidate)
        return True

    # Текстовый запасной вариант, если в сообществе выключены кнопки.
    if state.get("active_order_id"):
        text_actions = (
            ("подписать", "sign", "Подписать КП?"),
            ("оплат", "pay", "Провести тестовую оплату? Деньги не списываются."),
            ("подтверд", "confirm", "Подтвердить, что работа выполнена?"),
        )
        for marker, code, prompt in text_actions:
            if marker in lower:
                state["step"] = "client_confirm"
                state["pending_action"] = code
                state["pending_value"] = None
                await send(vk, user_id, prompt, keyboard=keyboards.confirm())
                return True
        if "документ" in lower or "прочитать" in lower:
            try:
                card = await api.client_order(int(state["active_order_id"]), -user_id)
            except APIError as exc:
                await send(vk, user_id, f"⚠️ {exc.message}")
                return True
            await send(vk, user_id, documents_text(card))
            await show_order_card(
                vk, api, user_id, profile, order_id=int(state["active_order_id"])
            )
            return True

    return False


async def show_pricing(
    vk: VKAPI, api: ConsultFlowAPI, user_id: int
) -> None:
    try:
        payload = await api.pricing()
    except APIError as exc:
        await send(vk, user_id, f"⚠️ {exc.message}", keyboard=keyboards.main_menu())
        return
    await send(vk, user_id, pricing_text(payload), keyboard=keyboards.main_menu())


async def show_dashboard_link(
    vk: VKAPI, api: ConsultFlowAPI, user_id: int
) -> None:
    try:
        link = await api.dashboard_link(-user_id)
    except APIError as exc:
        await send(vk, user_id, f"⚠️ {exc.message}", keyboard=keyboards.main_menu())
        return
    await send(
        vk,
        user_id,
        f"🖥 Ссылка на дашборд действует {link['expires_in_minutes']} минут:\n{link['url']}",
        keyboard=keyboards.main_menu(True),
    )


async def create_order(
    vk: VKAPI, api: ConsultFlowAPI, user_id: int, profile: dict[str, Any]
) -> None:
    session = _session(user_id)
    data = session.get("data", {})
    try:
        order = await api.create_order(
            telegram_id=-user_id,
            practice=data["practice"],
            title=data.get("title") or data["description"][:120],
            description=data["description"],
            hours=float(data["hours"]),
            complexity=data["complexity"],
            client_name=profile.get("vk_name") or "Клиент ВКонтакте",
            kp=data.get("kp"),
        )
    except (APIError, KeyError, ValueError) as exc:
        message = getattr(exc, "message", "Проверьте данные заявки.")
        await send(vk, user_id, f"⚠️ {message}", keyboard=keyboards.confirm())
        return

    _reset(user_id)
    estimate = order.get("estimate", {})
    text = (
        f"✅ Заявка №{order.get('number')} создана\n\n"
        f"Направление: {order.get('practice_label')}\n"
        f"Задача: {order.get('title')}\n"
        f"Предварительная стоимость: {money(order.get('amount', 0))}\n"
        f"Расчёт: {money(estimate.get('rate', 0))}/час × {estimate.get('hours', 0):g} ч "
        f"× {estimate.get('multiplier', 1)}\n\n"
        "Менеджер получил уведомление. Статус — в «Мои заявки».\n\n"
        "Дальше всё можно делать прямо в VK: прочитать КП и документы, "
        "подписать КП, провести тестовую оплату и подтвердить работу."
    )
    if data.get("kp"):
        text += "\n\n📄 Черновик КП сохранён в карточке заявки."
    try:
        link = await api.client_link(-user_id)
        text += f"\n\n🖥 Личный кабинет — заявка и документы:\n{link['url']}"
    except APIError:
        pass
    await send(vk, user_id, text, keyboard=keyboards.main_menu(bool(profile.get("is_manager"))))


async def ai_answer(
    vk: VKAPI,
    api: ConsultFlowAPI,
    user_id: int,
    text: str,
    profile: dict[str, Any] | None,
) -> None:
    settings = get_settings()
    if not settings.is_ai_configured:
        await send(
            vk,
            user_id,
            "🤖 ИИ-консультант пока не подключён. Добавьте POLZA_API_KEY в .env.",
            keyboard=keyboards.main_menu(bool(profile and profile.get("is_manager"))),
        )
        return

    await vk.set_typing(user_id)
    is_manager = bool(profile and profile.get("is_manager"))
    pricing: dict[str, Any] | None = None
    orders: list[dict[str, Any]] = []
    try:
        pricing = await api.pricing()
    except APIError:
        logger.warning("VK AI: pricing unavailable")
    try:
        if is_manager:
            orders = (await api.queue(-user_id))[:5]
        else:
            orders = await api.my_orders(-user_id, limit=5)
    except APIError:
        logger.warning("VK AI: orders unavailable")

    history = _history(user_id, max(2, settings.ai_history_limit))
    messages = [
        {
            "role": "system",
            "content": build_system_prompt(
                settings,
                pricing=pricing,
                orders=orders,
                is_manager=is_manager,
                client_name=(profile or {}).get("vk_name", ""),
            ),
        },
        *list(history),
        {"role": "user", "content": text[:2000]},
    ]
    client = PolzaClient(settings)
    try:
        answer = await client.complete(messages)
    except AIError as exc:
        await send(vk, user_id, f"⚠️ {exc.message}")
        return
    finally:
        await client.close()

    history.append({"role": "user", "content": text[:2000]})
    history.append({"role": "assistant", "content": answer})
    await send(vk, user_id, answer, keyboard=keyboards.main_menu(is_manager))


def _practice_from_text(text: str) -> tuple[str, str] | None:
    lower = text.lower().strip()
    for key, value in PRACTICES.items():
        if key in lower:
            return value
    return None


def _complexity_from_text(text: str) -> tuple[str, str] | None:
    lower = text.lower().strip()
    for key, value in COMPLEXITY.items():
        if key in lower:
            return value
    return None


async def handle_order_step(
    vk: VKAPI,
    api: ConsultFlowAPI,
    user_id: int,
    profile: dict[str, Any],
    text: str,
) -> bool:
    session = _session(user_id)
    step = session.get("step")
    data = session.setdefault("data", {})
    lower = text.lower().strip()

    if lower in {"отмена", "/cancel", "cancel", "назад"}:
        _reset(user_id)
        await send(
            vk,
            user_id,
            "Ок, заявка отменена.",
            keyboard=keyboards.main_menu(bool(profile.get("is_manager"))),
        )
        return True

    if step == "ai_request":
        if len(text) < 5:
            await send(vk, user_id, "Слишком коротко. Опишите задачу хотя бы одним предложением.")
            return True
        await analyze_ai_intake(vk, api, user_id, profile, text)
        return True

    if step == "ai_confirm":
        choice = lower.lstrip("✅✔️ ").strip()
        if choice.startswith(("создать", "подтверд")) or choice in {"да", "yes", "ок", "ok"}:
            analysis = data.get("analysis") or {}
            data.update(
                {
                    "practice": analysis.get("practice"),
                    "practice_label": analysis.get("practice_label"),
                    "title": analysis.get("title"),
                    "description": analysis.get("description"),
                    "hours": analysis.get("hours"),
                    "complexity": analysis.get("complexity"),
                    "kp": analysis.get("kp"),
                }
            )
            await create_order(vk, api, user_id, profile)
            return True
        if lower.startswith("отмен"):
            _reset(user_id)
            await send(
                vk,
                user_id,
                "Ок, заявка не создана.",
                keyboard=keyboards.main_menu(bool(profile.get("is_manager"))),
            )
            return True
        await send(
            vk,
            user_id,
            "Нажмите «Создать заявку» или «Отмена».",
            keyboard=keyboards.ai_confirm(),
        )
        return True

    if step == "practice":
        found = _practice_from_text(text)
        if not found:
            await send(vk, user_id, "Выберите направление кнопкой:", keyboard=keyboards.practices())
            return True
        data["practice"], data["practice_label"] = found
        session["step"] = "description"
        await send(
            vk,
            user_id,
            "Опишите задачу одним сообщением: что нужно сделать, "
            "какой результат ожидаете и есть ли сроки.",
            keyboard=keyboards.back(),
        )
        return True

    if step == "description":
        if len(text) < 5:
            await send(vk, user_id, "Слишком коротко. Опишите задачу хотя бы одним предложением.")
            return True
        data["description"] = text[:2000]
        data["title"] = text[:120]
        session["step"] = "hours"
        await send(
            vk,
            user_id,
            "Сколько часов примерно потребуется?",
            keyboard=keyboards.hours(),
        )
        return True

    if step == "hours":
        match = re.search(r"\d+", text)
        if not match:
            await send(vk, user_id, "Укажите число часов кнопкой или цифрой.", keyboard=keyboards.hours())
            return True
        hours = int(match.group())
        if hours < 1 or hours > 2000:
            await send(vk, user_id, "Часы должны быть от 1 до 2000. Попробуйте ещё раз.")
            return True
        data["hours"] = hours
        session["step"] = "complexity"
        await send(vk, user_id, "Выберите сложность:", keyboard=keyboards.complexity())
        return True

    if step == "complexity":
        found = _complexity_from_text(text)
        if not found:
            await send(vk, user_id, "Выберите сложность кнопкой:", keyboard=keyboards.complexity())
            return True
        data["complexity"], data["complexity_label"] = found
        session["step"] = "confirm"
        await send(
            vk,
            user_id,
            "Проверьте заявку:\n\n"
            f"Направление: {data['practice_label']}\n"
            f"Задача: {data['description']}\n"
            f"Часы: {data['hours']}\n"
            f"Сложность: {data['complexity_label']}\n\n"
            "Подтвердить отправку?",
            keyboard=keyboards.confirm(),
        )
        return True

    if step == "confirm":
        if lower.startswith("подтверд") or lower in {"да", "yes", "ок", "ok"}:
            await create_order(vk, api, user_id, profile)
            return True
        if lower.startswith("отмен"):
            _reset(user_id)
            await send(vk, user_id, "Заявка отменена.", keyboard=keyboards.main_menu())
            return True
        await send(vk, user_id, "Нажмите «Подтвердить» или «Отмена».", keyboard=keyboards.confirm())
        return True

    return False


async def handle_message(
    vk: VKAPI, api: ConsultFlowAPI, message: dict[str, Any]
) -> None:
    user_id = int(message.get("from_id") or 0)
    if user_id <= 0:
        return
    text = (message.get("text") or "").strip()
    if not text:
        await send(vk, user_id, "Напишите текстом или выберите кнопку в меню.")
        return

    profile = await ensure_profile(vk, api, user_id)
    if profile is None:
        await send(
            vk,
            user_id,
            "⚠️ Сервис ConsultFlow временно недоступен. Проверьте, что backend запущен.",
        )
        return

    lower = text.lower().strip()
    command = lower.split()[0] if lower.startswith("/") else ""

    if command == "/start" or lower in {
        "start",
        "начать",
        "меню",
        "главное меню",
        "🏠 главное меню",
    }:
        _histories.pop(user_id, None)
        await show_menu(vk, api, user_id, profile)
        return
    if command == "/cancel":
        _reset(user_id)
        await send(vk, user_id, "Ок, отменил.", keyboard=keyboards.main_menu(bool(profile.get("is_manager"))))
        return
    if command == "/id":
        note = (
            "Для роли менеджера добавьте в .env: "
            f"MANAGER_TELEGRAM_IDS=-{user_id} и перезапустите backend."
        )
        await send(
            vk,
            user_id,
            f"🆔 Ваш VK ID: {user_id}\n\n"
            f"Технический ID ConsultFlow: -{user_id}.\n{note}",
        )
        return
    if command == "/help" or "помощь" in lower:
        await send(
            vk,
            user_id,
            help_text(bool(profile.get("is_manager"))),
            keyboard=keyboards.main_menu(bool(profile.get("is_manager"))),
        )
        return

    if await handle_client_step(vk, api, user_id, profile, text):
        return

    if _session(user_id).get("step"):
        handled = await handle_order_step(vk, api, user_id, profile, text)
        if handled:
            return

    if "ai-заявка" in lower or "ии-заявка" in lower:
        await start_ai_intake(vk, user_id)
        return
    if "оставить заявку" in lower or lower in {"заявка", "новая заявка"}:
        await start_order(vk, user_id)
        return
    if "мои заявки" in lower or lower in {"заявки", "статус"}:
        await show_orders(vk, api, user_id, bool(profile.get("is_manager")))
        return
    if "прайс" in lower:
        await show_pricing(vk, api, user_id)
        return
    if "кабинет" in lower or "сайт" in lower or "прототип" in lower:
        await show_client_cabinet(vk, api, user_id, profile)
        return
    if "очередь" in lower and profile.get("is_manager"):
        await show_queue(vk, api, user_id)
        return
    if "дашборд" in lower and profile.get("is_manager"):
        await show_dashboard_link(vk, api, user_id)
        return
    if "спросить ии" in lower or lower in {"ии", "ai", "бот"}:
        await send(
            vk,
            user_id,
            "🤖 Напишите вопрос одним сообщением. Я помогу выбрать услугу, "
            "объясню этапы и сориентирую по стоимости. Точную смету подтверждает менеджер.",
            keyboard=keyboards.main_menu(bool(profile.get("is_manager"))),
        )
        return

    await ai_answer(vk, api, user_id, text, profile)


async def notification_worker(vk: VKAPI, api: ConsultFlowAPI, interval: float = 5.0) -> None:
    """Доставляет уведомления с отрицательными recipient — это VK-пользователи."""
    await asyncio.sleep(2)
    while True:
        try:
            items = await api.pending_notifications(limit=20)
            sent: list[int] = []
            failed: list[int] = []
            for item in items:
                try:
                    recipient = int(item.get("recipient", ""))
                except (TypeError, ValueError):
                    continue
                if recipient >= 0:
                    # Положительные ID принадлежат Telegram; не трогаем их.
                    continue
                keyboard = None
                order_id = item.get("order_id")
                if order_id:
                    try:
                        card = await api.client_order(int(order_id), recipient)
                        number = card.get("number")
                        if number:
                            keyboard = keyboards.order_open(str(number))
                    except (APIError, TypeError, ValueError) as exc:
                        logger.warning(
                            "VK notification %s: карточка недоступна: %s",
                            item.get("id"),
                            exc,
                        )
                try:
                    await send(
                        vk,
                        abs(recipient),
                        _clean(item.get("text", "")),
                        keyboard=keyboard,
                    )
                    sent.append(int(item["id"]))
                except (VKError, KeyError, TypeError) as exc:
                    logger.warning("VK notification %s failed: %s", item.get("id"), exc)
                    try:
                        failed.append(int(item["id"]))
                    except (KeyError, TypeError, ValueError):
                        pass
            if sent:
                await api.ack_notifications(sent)
                logger.info("VK: доставлено уведомлений %s", len(sent))
            if failed:
                await api.fail_notifications(failed)
                logger.info("VK: помечено недоставленных уведомлений %s", len(failed))
        except asyncio.CancelledError:
            raise
        except APIError as exc:
            logger.warning("VK notifications: API unavailable: %s", exc)
        except Exception:  # noqa: BLE001
            logger.exception("VK notifications loop failed")
        await asyncio.sleep(interval)


async def run() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # В URL Long Poll находится ключ сессии — не пишем его в INFO-логи.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    acquire_instance_lock()
    settings = get_settings()
    if not settings.is_vk_configured:
        logger.error(
            "VK не настроен. Укажите VK_TOKEN и VK_GROUP_ID в .env. "
            "Токен создаётся в настройках сообщества → API."
        )
        return

    api = ConsultFlowAPI(
        settings.backend_url, settings.bot_api_token, settings.request_timeout
    )
    vk = VKAPI(settings.vk_token, settings.vk_group_id_int)
    worker = asyncio.create_task(notification_worker(vk, api))
    try:
        try:
            server, key, ts = await vk.get_long_poll_server()
        except VKError as exc:
            logger.error(
                "Не удалось запустить VK Long Poll: %s. Проверьте VK_TOKEN, "
                "VK_GROUP_ID и включённый Long Poll API в настройках сообщества.",
                exc,
            )
            return
        logger.info(
            "VK-бот запущен: сообщество %s, Long Poll готов",
            settings.vk_group_id_int,
        )
        while True:
            try:
                data = await vk.poll(server, key, ts)
            except VKError as exc:
                logger.warning("VK Long Poll: %s; переподключаюсь", exc)
                await asyncio.sleep(5)
                server, key, ts = await vk.get_long_poll_server()
                continue

            if data.get("failed"):
                failed = int(data.get("failed") or 0)
                logger.warning("VK Long Poll failed=%s; обновляю параметры", failed)
                if failed == 1 and data.get("ts"):
                    ts = int(data["ts"])
                    continue
                server, key, ts = await vk.get_long_poll_server()
                continue

            ts = int(data.get("ts") or ts)
            for update in data.get("updates", []):
                if update.get("type") != "message_new":
                    continue
                message = (update.get("object") or {}).get("message") or {}
                if message.get("out"):
                    continue
                if _is_duplicate_message(message):
                    logger.info(
                        "VK: пропущено повторное событие сообщения %s",
                        message.get("id"),
                    )
                    continue
                try:
                    await handle_message(vk, api, message)
                except Exception:  # noqa: BLE001
                    logger.exception("VK message handler failed")
    finally:
        worker.cancel()
        await api.close()
        await vk.close()


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("VK-бот остановлен")


if __name__ == "__main__":
    main()
