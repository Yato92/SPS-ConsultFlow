"""Пошаговое оформление заявки через FSM."""

import html
import re

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from consultflow_bot import views
from consultflow_bot.api import APIError, ConsultFlowAPI
from consultflow_bot.keyboards import (
    after_order,
    client_menu,
    complexity_options,
    confirm_order,
    hours_options,
    practices,
    skip_button,
)
from consultflow_bot.states import OrderForm
from consultflow_bot.utils import safe_edit

router = Router(name="order")


def _summary(data: dict) -> str:
    complexity_label, multiplier = views.COMPLEXITY[data["complexity"]]
    lines = [
        "🧾 <b>Проверьте заявку</b>",
        "",
        f"Направление: <b>{views.PRACTICES[data['practice']]}</b>",
        f"Задача: {html.escape(data['title'])}",
    ]
    if data.get("description"):
        lines.append(f"Описание: {html.escape(data['description'])}")
    lines.extend(
        [
            f"Объём работ: {data['hours']} ч",
            f"Сложность: {complexity_label} (×{multiplier})",
        ]
    )
    if data.get("client_name"):
        lines.append(f"Компания: {html.escape(data['client_name'])}")
    if data.get("phone"):
        lines.append(f"Телефон: {html.escape(data['phone'])}")
    lines.extend(
        [
            "",
            "После подтверждения заявка попадёт менеджеру, "
            "а бот рассчитает предварительную стоимость и срок ответа.",
        ]
    )
    return "\n".join(lines)


@router.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Заполнение заявки отменено.", reply_markup=client_menu())


@router.callback_query(F.data == "order:new")
async def start_order(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    await state.set_state(OrderForm.practice)
    await safe_edit(
        callback.message,
        "📝 <b>Новая заявка</b>\n\n"
        "<b>Шаг 1 из 6.</b> Выберите направление консалтинга:",
        practices(),
    )


@router.callback_query(StateFilter(OrderForm.practice), F.data.startswith("order:practice:"))
async def choose_practice(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[-1]
    if value not in views.PRACTICES:
        await callback.answer("Неизвестное направление", show_alert=True)
        return
    await callback.answer()
    await state.update_data(practice=value)
    await state.set_state(OrderForm.title)
    await callback.message.answer(
        f"Направление: <b>{views.PRACTICES[value]}</b>\n\n"
        "<b>Шаг 2 из 6.</b> Опишите задачу одной строкой.\n"
        "Например: «Аудит ИТ-инфраструктуры и план миграции в облако».\n\n"
        "Для отмены — /cancel."
    )


@router.message(StateFilter(OrderForm.title))
async def enter_title(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) < 3:
        await message.answer("Слишком коротко. Опишите задачу минимум тремя символами.")
        return
    if len(text) > 200:
        await message.answer("Слишком длинно (максимум 200 символов). Сократите формулировку.")
        return
    await state.update_data(title=text)
    await state.set_state(OrderForm.description)
    await message.answer(
        "<b>Шаг 3 из 6.</b> Добавьте детали: что уже есть, какой результат нужен, "
        "какие сроки важны.\n\n"
        "Можно пропустить.",
        reply_markup=skip_button("description"),
    )


@router.callback_query(StateFilter(OrderForm.description), F.data == "order:skip:description")
async def skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(description=None)
    await state.set_state(OrderForm.hours)
    await callback.message.answer(
        "<b>Шаг 4 из 6.</b> Сколько часов работы консультантов требуется?\n"
        "Выберите вариант или отправьте число сообщением.",
        reply_markup=hours_options(),
    )


@router.message(StateFilter(OrderForm.description))
async def enter_description(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) > 1000:
        await message.answer("Описание слишком длинное (максимум 1000 символов).")
        return
    await state.update_data(description=text)
    await state.set_state(OrderForm.hours)
    await message.answer(
        "<b>Шаг 4 из 6.</b> Сколько часов работы консультантов требуется?\n"
        "Выберите вариант или отправьте число сообщением.",
        reply_markup=hours_options(),
    )


@router.callback_query(StateFilter(OrderForm.hours), F.data.startswith("order:hours:"))
async def choose_hours(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[-1]
    if not value.isdigit() or not 1 <= int(value) <= 2000:
        await callback.answer("Некорректное значение", show_alert=True)
        return
    await callback.answer()
    await _ask_complexity(callback.message, state, int(value))


@router.message(StateFilter(OrderForm.hours))
async def enter_hours(message: Message, state: FSMContext) -> None:
    digits = re.sub(r"\D", "", message.text or "")
    if not digits or not 1 <= int(digits) <= 2000:
        await message.answer("Введите целое число часов от 1 до 2000.")
        return
    await _ask_complexity(message, state, int(digits))


async def _ask_complexity(message: Message, state: FSMContext, hours: int) -> None:
    await state.update_data(hours=hours)
    await state.set_state(OrderForm.complexity)
    await message.answer(
        f"Объём: <b>{hours} ч</b>\n\n"
        "<b>Шаг 5 из 6.</b> Выберите сложность проекта — от неё зависит коэффициент к ставке.",
        reply_markup=complexity_options(),
    )


@router.callback_query(StateFilter(OrderForm.complexity), F.data.startswith("order:complexity:"))
async def choose_complexity(callback: CallbackQuery, state: FSMContext) -> None:
    value = callback.data.split(":")[-1]
    if value not in views.COMPLEXITY:
        await callback.answer("Некорректное значение", show_alert=True)
        return
    await callback.answer()
    await state.update_data(complexity=value)
    await state.set_state(OrderForm.client_name)
    await callback.message.answer(
        "<b>Шаг 6 из 6.</b> Как называется ваша компания?\n"
        "Это нужно для договора. Можно пропустить.",
        reply_markup=skip_button("client_name"),
    )


@router.callback_query(StateFilter(OrderForm.client_name), F.data == "order:skip:client_name")
async def skip_client_name(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(client_name=None)
    await state.set_state(OrderForm.phone)
    await callback.message.answer(
        "Укажите телефон для связи или пропустите шаг.",
        reply_markup=skip_button("phone"),
    )


@router.message(StateFilter(OrderForm.client_name))
async def enter_client_name(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if len(text) > 200:
        await message.answer("Слишком длинное название (максимум 200 символов).")
        return
    await state.update_data(client_name=text)
    await state.set_state(OrderForm.phone)
    await message.answer(
        "Укажите телефон для связи или пропустите шаг.",
        reply_markup=skip_button("phone"),
    )


@router.callback_query(StateFilter(OrderForm.phone), F.data == "order:skip:phone")
async def skip_phone(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.update_data(phone=None)
    await _ask_confirm(callback.message, state)


@router.message(StateFilter(OrderForm.phone))
async def enter_phone(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not re.fullmatch(r"[0-9+\-() ]{5,40}", text):
        await message.answer(
            "Похоже, это не телефон. Используйте цифры, пробелы, «+», «-» и скобки."
        )
        return
    await state.update_data(phone=text)
    await _ask_confirm(message, state)


async def _ask_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(OrderForm.confirm)
    await message.answer(_summary(data), reply_markup=confirm_order())


@router.callback_query(StateFilter(OrderForm.confirm), F.data == "order:confirm")
async def confirm_order_handler(
    callback: CallbackQuery, state: FSMContext, api: ConsultFlowAPI
) -> None:
    await callback.answer()
    data = await state.get_data()
    if not data.get("practice") or not data.get("title"):
        await state.clear()
        await callback.message.answer(
            "Данные заявки потерялись. Начните заново: /menu", reply_markup=client_menu()
        )
        return

    await state.clear()
    try:
        order = await api.create_order(
            telegram_id=callback.from_user.id,
            practice=data["practice"],
            title=data["title"],
            description=data.get("description"),
            hours=int(data["hours"]),
            complexity=data["complexity"],
            client_name=data.get("client_name"),
            phone=data.get("phone"),
        )
    except APIError as exc:
        await callback.message.answer(f"⚠️ Не удалось создать заявку: {html.escape(exc.message)}")
        return

    await callback.message.answer(views.order_created_text(order), reply_markup=after_order())


@router.callback_query(F.data == "order:cancel")
async def cancel_order(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Заявка отменена")
    await safe_edit(
        callback.message,
        "Заполнение заявки отменено. Вы можете начать заново в любой момент.",
        client_menu(),
    )
