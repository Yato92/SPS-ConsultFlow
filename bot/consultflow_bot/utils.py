"""Вспомогательное форматирование сообщений бота."""

from datetime import datetime

from aiogram.types import Message

STATUS_EMOJI = {
    "new": "🆕",
    "qualified": "✅",
    "proposal": "📄",
    "approved": "👍",
    "contract": "🖊",
    "in_progress": "⚙️",
    "done": "🏁",
    "closed": "🔒",
    "cancelled": "❌",
}


def money(value: float | int) -> str:
    return f"{float(value):,.0f}".replace(",", " ") + " ₽"


def fmt_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return value
    return parsed.strftime("%d.%m.%Y %H:%M")


def short_date(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value).strftime("%d.%m.%Y")
    except ValueError:
        return value


def status_line(status: str, label: str) -> str:
    return f"{STATUS_EMOJI.get(status, '•')} {label}"


async def safe_edit(message: Message, text: str, reply_markup=None) -> None:
    """Редактирует сообщение, а если не удалось — отправляет новое."""
    from aiogram.exceptions import TelegramBadRequest

    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await message.answer(text, reply_markup=reply_markup)
