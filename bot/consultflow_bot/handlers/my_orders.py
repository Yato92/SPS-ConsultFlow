"""Просмотр заявок клиентом."""

import html

from aiogram import F, Router
from aiogram.types import CallbackQuery

from consultflow_bot import views
from consultflow_bot.api import APIError, ConsultFlowAPI
from consultflow_bot.keyboards import back_to_orders, my_orders as my_orders_kb
from consultflow_bot.utils import safe_edit

router = Router(name="my_orders")


@router.callback_query(F.data == "my:list")
async def show_my_orders(callback: CallbackQuery, api: ConsultFlowAPI) -> None:
    await callback.answer()
    try:
        items = await api.my_orders(callback.from_user.id, limit=10)
    except APIError as exc:
        await callback.message.answer(f"⚠️ {html.escape(exc.message)}")
        return

    if not items:
        await safe_edit(callback.message, views.my_orders_text([]), my_orders_kb([]))
        return
    await safe_edit(callback.message, views.my_orders_text(items), my_orders_kb(items))


@router.callback_query(F.data.startswith("my:detail:"))
async def show_order_detail(callback: CallbackQuery, api: ConsultFlowAPI) -> None:
    number = callback.data.split(":", 2)[2]
    await callback.answer()
    try:
        order = await api.order_detail(number, callback.from_user.id)
    except APIError as exc:
        await callback.message.answer(f"⚠️ {html.escape(exc.message)}")
        return
    await safe_edit(callback.message, views.order_detail_text(order), back_to_orders())
