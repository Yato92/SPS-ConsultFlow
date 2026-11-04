"""Общие команды и главное меню."""

import html

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from consultflow_bot import views
from consultflow_bot.ai import reset_history
from consultflow_bot.api import APIError, ConsultFlowAPI
from consultflow_bot.keyboards import back_to_client_menu, client_menu, manager_menu
from consultflow_bot.utils import safe_edit

router = Router(name="common")


async def _register(api: ConsultFlowAPI, message: Message) -> dict:
    user = message.from_user
    return await api.register(user.id, user.username, user.full_name)


@router.message(CommandStart())
async def cmd_start(message: Message, api: ConsultFlowAPI, state: FSMContext) -> None:
    await state.clear()
    reset_history(message.from_user.id)
    try:
        data = await _register(api, message)
    except APIError as exc:
        await message.answer(f"⚠️ {html.escape(exc.message)}")
        return

    is_manager = bool(data["is_manager"])
    markup = manager_menu() if is_manager else client_menu()
    await message.answer(
        views.welcome_text(message.from_user.full_name, is_manager),
        reply_markup=markup,
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, api: ConsultFlowAPI, state: FSMContext) -> None:
    await state.clear()
    reset_history(message.from_user.id)
    try:
        data = await _register(api, message)
    except APIError as exc:
        await message.answer(f"⚠️ {html.escape(exc.message)}")
        return

    if data["is_manager"]:
        await message.answer(
            views.manager_menu_text(message.from_user.full_name),
            reply_markup=manager_menu(),
        )
    else:
        await message.answer(
            views.welcome_text(message.from_user.full_name, False),
            reply_markup=client_menu(),
        )


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery, api: ConsultFlowAPI, state: FSMContext) -> None:
    await callback.answer()
    await state.clear()
    reset_history(callback.from_user.id)
    try:
        data = await api.register(
            callback.from_user.id, callback.from_user.username, callback.from_user.full_name
        )
    except APIError as exc:
        await callback.message.answer(f"⚠️ {html.escape(exc.message)}")
        return

    if data["is_manager"]:
        await safe_edit(
            callback.message,
            views.manager_menu_text(callback.from_user.full_name),
            manager_menu(),
        )
    else:
        await safe_edit(
            callback.message,
            views.welcome_text(callback.from_user.full_name, False),
            client_menu(),
        )


@router.message(Command("help"))
async def cmd_help(message: Message, api: ConsultFlowAPI) -> None:
    try:
        data = await _register(api, message)
    except APIError:
        data = {"is_manager": False}
    await message.answer(
        views.help_text(bool(data["is_manager"])),
        reply_markup=manager_menu() if data["is_manager"] else client_menu(),
    )


@router.callback_query(F.data == "menu:help")
async def help_callback(callback: CallbackQuery, api: ConsultFlowAPI) -> None:
    await callback.answer()
    try:
        data = await api.register(
            callback.from_user.id, callback.from_user.username, callback.from_user.full_name
        )
        is_manager = bool(data["is_manager"])
    except APIError:
        is_manager = False
    await safe_edit(
        callback.message,
        views.help_text(is_manager),
        manager_menu() if is_manager else back_to_client_menu(),
    )


@router.message(Command("pricing"))
async def cmd_pricing(message: Message, api: ConsultFlowAPI) -> None:
    try:
        payload = await api.pricing()
    except APIError as exc:
        await message.answer(f"⚠️ {html.escape(exc.message)}")
        return
    await message.answer(views.pricing_text(payload), reply_markup=back_to_client_menu())


@router.callback_query(F.data == "menu:pricing")
async def pricing_callback(callback: CallbackQuery, api: ConsultFlowAPI) -> None:
    await callback.answer()
    try:
        payload = await api.pricing()
    except APIError as exc:
        await callback.message.answer(f"⚠️ {html.escape(exc.message)}")
        return
    await safe_edit(callback.message, views.pricing_text(payload), back_to_client_menu())


@router.message(Command("id"))
async def cmd_id(message: Message) -> None:
    await message.answer(
        f"🆔 Ваш Telegram ID: <code>{message.from_user.id}</code>\n\n"
        "Передайте его администратору, чтобы получить роль менеджера."
    )


@router.message(Command("link"))
async def cmd_link(message: Message, api: ConsultFlowAPI) -> None:
    try:
        link = await api.dashboard_link(message.from_user.id)
    except APIError as exc:
        await message.answer(f"⚠️ {html.escape(exc.message)}")
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    kb = InlineKeyboardBuilder()
    kb.button(text="🖥 Открыть дашборд", url=link["url"])
    kb.adjust(1)
    await message.answer(
        "🖥 <b>Дашборд ConsultFlow</b>\n\n"
        f"Одноразовая ссылка действует {link['expires_in_minutes']} минут:\n"
        f'<a href="{link["url"]}">открыть дашборд</a>',
        reply_markup=kb.as_markup(),
    )
