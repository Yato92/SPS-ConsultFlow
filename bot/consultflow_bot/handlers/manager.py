"""Кабинет менеджера: очередь, статусы, статистика и дашборд."""

import html

from aiogram import F, Router
from aiogram.types import CallbackQuery

from consultflow_bot import views
from consultflow_bot.api import APIError, ConsultFlowAPI
from consultflow_bot.keyboards import (
    back_to_manager_menu,
    dashboard_link,
    manager_order_actions,
    manager_queue,
    stats_actions,
)
from consultflow_bot.utils import safe_edit

router = Router(name="manager")


async def _ensure_manager(callback: CallbackQuery, api: ConsultFlowAPI) -> bool:
    try:
        data = await api.register(
            callback.from_user.id, callback.from_user.username, callback.from_user.full_name
        )
    except APIError as exc:
        await callback.answer(f"⚠️ {exc.message}", show_alert=True)
        return False
    if not data["is_manager"]:
        await callback.answer("Раздел доступен только менеджерам", show_alert=True)
        return False
    return True


@router.callback_query(F.data == "mgr:queue")
async def queue(callback: CallbackQuery, api: ConsultFlowAPI) -> None:
    await callback.answer()
    if not await _ensure_manager(callback, api):
        return
    try:
        items = await api.queue(callback.from_user.id)
    except APIError as exc:
        await callback.message.answer(f"⚠️ {html.escape(exc.message)}")
        return
    await safe_edit(callback.message, views.queue_text(items), manager_queue(items))


@router.callback_query(F.data.startswith("mgr:order:"))
async def order_card(callback: CallbackQuery, api: ConsultFlowAPI) -> None:
    number = callback.data.split(":", 2)[2]
    await callback.answer()
    if not await _ensure_manager(callback, api):
        return
    try:
        order = await api.order_detail(number, callback.from_user.id)
    except APIError as exc:
        await callback.message.answer(f"⚠️ {html.escape(exc.message)}")
        return
    await safe_edit(
        callback.message, views.order_detail_text(order), manager_order_actions(order)
    )


@router.callback_query(F.data.startswith("mgr:set:"))
async def set_status(callback: CallbackQuery, api: ConsultFlowAPI) -> None:
    parts = callback.data.split(":")
    if len(parts) != 4 or not parts[2].isdigit():
        await callback.answer("Некорректная команда", show_alert=True)
        return
    order_id = int(parts[2])
    new_status = parts[3]
    await callback.answer("Обновляю статус…")
    if not await _ensure_manager(callback, api):
        return
    try:
        order = await api.change_status(
            order_id=order_id,
            telegram_id=callback.from_user.id,
            status=new_status,
            comment="Статус изменён через Telegram-бота",
        )
    except APIError as exc:
        await callback.message.answer(f"⚠️ {html.escape(exc.message)}")
        return
    await safe_edit(
        callback.message, views.order_detail_text(order), manager_order_actions(order)
    )


@router.callback_query(F.data == "mgr:stats")
async def stats(callback: CallbackQuery, api: ConsultFlowAPI) -> None:
    await callback.answer()
    if not await _ensure_manager(callback, api):
        return
    try:
        payload = await api.stats(callback.from_user.id)
    except APIError as exc:
        await callback.message.answer(f"⚠️ {html.escape(exc.message)}")
        return
    await safe_edit(callback.message, views.stats_text(payload), stats_actions())


@router.callback_query(F.data == "mgr:link")
async def link(callback: CallbackQuery, api: ConsultFlowAPI) -> None:
    await callback.answer()
    if not await _ensure_manager(callback, api):
        return
    try:
        payload = await api.dashboard_link(callback.from_user.id)
    except APIError as exc:
        await callback.message.answer(f"⚠️ {html.escape(exc.message)}")
        return

    text = (
        "🖥 <b>Дашборд ConsultFlow</b>\n\n"
        "Ссылка персональная и одноразовая: она открывает дашборд "
        "под вашей учётной записью.\n"
        f"Срок действия — {payload['expires_in_minutes']} минут.\n\n"
        f'<a href="{payload["url"]}">Открыть дашборд</a>'
    )
    await safe_edit(callback.message, text, dashboard_link(payload["url"]))


@router.callback_query(F.data == "mgr:menu")
async def manager_menu_callback(callback: CallbackQuery) -> None:
    await callback.answer()
    await safe_edit(
        callback.message,
        "🖥 <b>Меню менеджера</b>\n\nВыберите действие.",
        back_to_manager_menu(),
    )
