"""Ответы на неизвестные команды и устаревшие кнопки."""

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from consultflow_bot.keyboards import client_menu

router = Router(name="fallback")

HINT = (
    "Я не понял команду. Воспользуйтесь меню: /menu\n"
    "Или посмотрите подсказку: /help"
)


@router.message(F.text)
async def unknown_message(message: Message) -> None:
    await message.answer(HINT, reply_markup=client_menu())


@router.callback_query()
async def stale_callback(callback: CallbackQuery) -> None:
    await callback.answer("Кнопка устарела. Откройте меню заново: /menu", show_alert=True)
