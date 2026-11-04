"""Клавиатуры Telegram-бота."""

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from consultflow_bot.config import get_settings
from consultflow_bot.utils import money


def client_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Оставить заявку", callback_data="order:new")
    kb.button(text="📋 Мои заявки", callback_data="my:list")
    kb.button(text="🖥 Открыть кабинет", url=get_settings().prototype_url)
    kb.button(text="💰 Прайс-лист", callback_data="menu:pricing")
    kb.button(text="❓ Как это работает", callback_data="menu:help")
    kb.adjust(1)
    return kb.as_markup()


def manager_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📥 Очередь заявок", callback_data="mgr:queue")
    kb.button(text="📊 Статистика", callback_data="mgr:stats")
    kb.button(text="🖥 Открыть дашборд", callback_data="mgr:link")
    kb.button(text="🧪 Открыть прототип", url=get_settings().prototype_url)
    kb.button(text="💰 Прайс-лист", callback_data="menu:pricing")
    kb.button(text="❓ Помощь", callback_data="menu:help")
    kb.adjust(1)
    return kb.as_markup()


def back_to_client_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Главное меню", callback_data="menu:home")
    return kb.as_markup()


def back_to_manager_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Главное меню", callback_data="menu:home")
    return kb.as_markup()


def practices() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🧭 Управленческий", callback_data="order:practice:management")
    kb.button(text="💵 Финансовый", callback_data="order:practice:finance")
    kb.button(text="⚖️ Юридический", callback_data="order:practice:legal")
    kb.button(text="💻 IT-консалтинг", callback_data="order:practice:it")
    kb.button(text="✖️ Отмена", callback_data="order:cancel")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def hours_options() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for hours in (8, 16, 24, 40, 80):
        kb.button(text=f"{hours} ч", callback_data=f"order:hours:{hours}")
    kb.button(text="✖️ Отмена", callback_data="order:cancel")
    kb.adjust(3, 2, 1)
    return kb.as_markup()


def complexity_options() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="Базовая ×1.0", callback_data="order:complexity:basic")
    kb.button(text="Стандартная ×1.25", callback_data="order:complexity:standard")
    kb.button(text="Сложная ×1.6", callback_data="order:complexity:complex")
    kb.button(text="✖️ Отмена", callback_data="order:cancel")
    kb.adjust(1)
    return kb.as_markup()


def skip_button(field: str, text: str = "⏭ Пропустить") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=text, callback_data=f"order:skip:{field}")
    kb.button(text="✖️ Отмена", callback_data="order:cancel")
    kb.adjust(1)
    return kb.as_markup()


def confirm_order() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить заявку", callback_data="order:confirm")
    kb.button(text="✖️ Отмена", callback_data="order:cancel")
    kb.adjust(1)
    return kb.as_markup()


def after_order() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Мои заявки", callback_data="my:list")
    kb.button(text="🏠 Главное меню", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def my_orders(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.button(
            text=f"№{item['number']} · {item['status_label']} · {money(item['amount'])}",
            callback_data=f"my:detail:{item['number']}",
        )
    kb.button(text="🏠 Главное меню", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def back_to_orders() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 К списку заявок", callback_data="my:list")
    kb.button(text="🏠 Главное меню", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


NEXT_ACTIONS = {
    "new": ("qualified", "✅ Квалифицировать"),
    "clarification": ("proposal", "📄 Отправить КП"),
    "qualified": ("proposal", "📄 Отправить КП"),
    "proposal": ("approved", "👍 КП согласовано"),
    "revision": ("proposal", "📄 Отправить обновлённое КП"),
    "approved": ("contract", "🖊 Договор подписан"),
    "contract": ("in_progress", "⚙️ В работу"),
    "in_progress": ("done", "🏁 Работы выполнены"),
    "done": ("closed", "🔒 Закрыть заказ"),
}


def manager_order_actions(order: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    action = NEXT_ACTIONS.get(order["status"])
    if action:
        next_status, label = action
        kb.button(
            text=label,
            callback_data=f"mgr:set:{order['id']}:{next_status}",
        )
    kb.button(text="🔄 Обновить", callback_data=f"mgr:order:{order['number']}")
    kb.button(text="📥 К очереди", callback_data="mgr:queue")
    kb.button(text="🏠 Главное меню", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def manager_queue(items: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.button(
            text=f"№{item['number']} · {item['status_label']} · {money(item['amount'])}",
            callback_data=f"mgr:order:{item['number']}",
        )
    kb.button(text="🔄 Обновить", callback_data="mgr:queue")
    kb.button(text="🏠 Главное меню", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def stats_actions() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🖥 Открыть дашборд", callback_data="mgr:link")
    kb.button(text="🔄 Обновить", callback_data="mgr:stats")
    kb.button(text="📥 Очередь заявок", callback_data="mgr:queue")
    kb.button(text="🏠 Главное меню", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()


def dashboard_link(url: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🖥 Открыть дашборд", url=url)
    kb.button(text="🔄 Новая ссылка", callback_data="mgr:link")
    kb.button(text="🏠 Главное меню", callback_data="menu:home")
    kb.adjust(1)
    return kb.as_markup()
