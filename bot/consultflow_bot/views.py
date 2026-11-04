"""Формирование текстов сообщений бота."""

import html

from consultflow_bot.utils import STATUS_EMOJI, fmt_date, money, short_date

PRACTICES = {
    "management": "Управленческий консалтинг",
    "finance": "Финансовый консалтинг",
    "legal": "Юридический консалтинг",
    "it": "IT-консалтинг",
}

COMPLEXITY = {
    "basic": ("Базовая", 1.0),
    "standard": ("Стандартная", 1.25),
    "complex": ("Сложная", 1.6),
}

STATUS_LABELS = {
    "new": "Новая заявка",
    "qualified": "Квалифицирована",
    "proposal": "КП отправлено",
    "approved": "КП согласовано",
    "contract": "Договор подписан",
    "in_progress": "В работе",
    "done": "Работы выполнены",
    "closed": "Закрыт",
    "cancelled": "Отменён",
}


def welcome_text(name: str, is_manager: bool) -> str:
    if is_manager:
        return (
            f"👋 <b>{html.escape(name)}</b>, здравствуйте!\n\n"
            "Вы вошли как <b>менеджер ConsultFlow</b>.\n"
            "Здесь можно принимать заявки, двигать их по статусам "
            "и смотреть сводную аналитику.\n\n"
            "Выберите действие ниже."
        )
    return (
        f"👋 <b>{html.escape(name)}</b>, здравствуйте!\n\n"
        "Это <b>ConsultFlow</b> — от заявки до акта один процесс.\n"
        "Оставьте заявку на консалтинговую услугу: бот рассчитает "
        "предварительную стоимость и срок ответа, а менеджер свяжется с вами.\n\n"
        "Выберите действие ниже."
    )


def manager_menu_text(name: str) -> str:
    return (
        f"🖥 <b>Меню менеджера</b>\n\n"
        f"{html.escape(name)}, в очереди вас ждут новые заявки.\n\n"
        "• <b>Очередь заявок</b> — принять заявку и сменить статус.\n"
        "• <b>Статистика</b> — ключевые показатели за всё время.\n"
        "• <b>Дашборд</b> — полная аналитика в браузере по одноразовой ссылке."
    )


def help_text(is_manager: bool) -> str:
    if is_manager:
        return (
            "❓ <b>Как работает бот для менеджера</b>\n\n"
            "1. Новая заявка приходит вам сообщением.\n"
            "2. Откройте «Очередь заявок» и выберите заказ.\n"
            "3. Переводите заказ по статусам: квалификация → КП → договор → "
            "работа → акт → закрытие.\n"
            "4. Документы формируются автоматически при смене статуса.\n"
            "5. «Открыть дашборд» — одноразовая ссылка на полную аналитику.\n\n"
            "Команды: /menu — меню, /link — ссылка на дашборд, /id — ваш Telegram ID."
        )
    return (
        "❓ <b>Как оставить заявку</b>\n\n"
        "1. Нажмите «Оставить заявку».\n"
        "2. Выберите направление консалтинга.\n"
        "3. Опишите задачу и укажите объём работ в часах.\n"
        "4. Подтвердите заявку — бот рассчитает стоимость и срок ответа.\n\n"
        "Статус заявки можно посмотреть в разделе «Мои заявки». "
        "Менеджер получит уведомление сразу после подтверждения.\n\n"
        "Команды: /menu — меню, /cancel — отменить заполнение."
    )


def pricing_text(payload: dict) -> str:
    lines = ["💰 <b>Прайс-лист ConsultFlow</b>", "", "<b>Направления</b>"]
    for item in payload["practices"]:
        lines.append(
            f"• {html.escape(item['label'])} — {money(item['rate'])}/час, "
            f"SLA {item['sla_hours']} ч"
        )
    lines.append("")
    lines.append("<b>Коэффициенты сложности</b>")
    for item in payload["complexities"]:
        lines.append(f"• {html.escape(item['label'])} — ×{item['multiplier']}")
    lines.append("")
    lines.append(
        "Итоговая стоимость = ставка × часы × коэффициент. "
        "Точную смету подтверждает менеджер после квалификации заявки."
    )
    return "\n".join(lines)


def order_created_text(order: dict) -> str:
    estimate = order.get("estimate", {})
    sla = order.get("sla_due_at")
    return (
        f"✅ <b>Заявка №{order['number']} создана</b>\n\n"
        f"Направление: {html.escape(order['practice_label'])}\n"
        f"Задача: {html.escape(order['title'])}\n"
        f"Предварительная стоимость: <b>{money(order['amount'])}</b>\n"
        f"Расчёт: {money(estimate.get('rate', 0))}/час × {estimate.get('hours', 0):g} ч "
        f"× {estimate.get('multiplier', 1)}\n"
        f"Срок ответа менеджера: <b>{fmt_date(sla)}</b>\n\n"
        "Менеджер уже получил уведомление. Следите за статусом в «Мои заявки»."
    )


def my_orders_text(items: list[dict]) -> str:
    if not items:
        return (
            "📋 <b>Мои заявки</b>\n\n"
            "Пока заявок нет. Нажмите «Оставить заявку», чтобы создать первую."
        )
    lines = ["📋 <b>Мои заявки</b>", ""]
    for item in items:
        emoji = STATUS_EMOJI.get(item["status"], "•")
        lines.append(
            f"{emoji} <b>№{item['number']}</b> · {html.escape(item['title'])}\n"
            f"    {item['status_label']} · {money(item['amount'])} · {short_date(item['created_at'])}"
        )
    lines.append("")
    lines.append("Нажмите на заявку, чтобы увидеть подробности.")
    return "\n".join(lines)


def order_detail_text(order: dict) -> str:
    emoji = STATUS_EMOJI.get(order["status"], "•")
    lines = [
        f"🧾 <b>Заказ №{order['number']}</b>",
        "",
        f"📌 {html.escape(order['title'])}",
        f"Статус: {emoji} <b>{order['status_label']}</b>",
        f"Направление: {html.escape(order['practice_label'])}",
        f"Клиент: {html.escape(order.get('client_name') or '—')}",
        f"Сумма: <b>{money(order['amount'])}</b>",
        f"Создан: {fmt_date(order['created_at'])}",
        f"SLA: {fmt_date(order.get('sla_due_at'))}"
        + (" ⚠️ <b>просрочен</b>" if order.get("is_overdue") else ""),
    ]
    if order.get("description"):
        lines.extend(["", f"📝 {html.escape(order['description'])}"])

    events = order.get("events") or []
    if events:
        lines.extend(["", "<b>История</b>"])
        for event in events[-6:]:
            label = STATUS_LABELS.get(event["to_status"], event["to_status"])
            lines.append(f"• {fmt_date(event['created_at'])} — {label}")
    return "\n".join(lines)


def queue_text(items: list[dict]) -> str:
    if not items:
        return "📥 <b>Очередь пуста</b>\n\nНовых заявок нет — все обращения обработаны."
    lines = [f"📥 <b>Очередь заявок</b> — {len(items)}", ""]
    for item in items:
        emoji = STATUS_EMOJI.get(item["status"], "•")
        lines.append(
            f"{emoji} <b>№{item['number']}</b> · {html.escape(item['title'])}\n"
            f"    {item['status_label']} · {money(item['amount'])} · {short_date(item['created_at'])}"
        )
    lines.append("")
    lines.append("Выберите заявку, чтобы открыть карточку и сменить статус.")
    return "\n".join(lines)


def stats_text(stats: dict) -> str:
    return (
        "📊 <b>Сводка ConsultFlow</b>\n\n"
        f"Всего заказов: <b>{stats['orders_total']}</b>\n"
        f"В работе: {stats['active_orders']}\n"
        f"Новых заявок: {stats['new_orders']}\n"
        f"Оплачено: <b>{money(stats['paid_total'])}</b>\n"
        f"Финансовый результат: <b>{money(stats['profit'])}</b>\n"
        f"Просрочено по SLA: {stats['overdue_count']}\n"
        f"Конверсия в закрытие: {stats['conversion']} %\n\n"
        f"Обновлено: {fmt_date(stats['generated_at'])}\n"
        "Полная аналитика доступна в дашборде."
    )
