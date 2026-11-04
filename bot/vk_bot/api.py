"""Минимальный клиент VK API для сообщества."""

from __future__ import annotations

import logging
import secrets
from typing import Any

import httpx

logger = logging.getLogger(__name__)

VK_API = "https://api.vk.com/method"


class VKError(Exception):
    """Ошибка VK API."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class VKAPI:
    def __init__(
        self,
        token: str,
        group_id: int,
        *,
        version: str = "5.199",
        timeout: float = 35.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._token = token
        self._group_id = group_id
        self._version = version
        self._client = httpx.AsyncClient(
            transport=transport,
            timeout=httpx.Timeout(timeout, connect=15.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def call(self, method: str, **params: Any) -> Any:
        payload = {
            **params,
            "access_token": self._token,
            "v": self._version,
        }
        try:
            response = await self._client.post(f"{VK_API}/{method}", data=payload)
        except httpx.HTTPError as exc:
            raise VKError("Нет связи с VK API. Проверьте интернет.") from exc

        if response.status_code >= 400:
            raise VKError(f"VK API вернул HTTP {response.status_code}.")

        try:
            data = response.json()
        except ValueError as exc:
            raise VKError("VK API вернул некорректный ответ.") from exc

        error = data.get("error")
        if error:
            code = int(error.get("error_code") or 0) or None
            message = str(error.get("error_msg") or "Неизвестная ошибка VK API")
            logger.warning("VK API %s: %s (%s)", method, message, code)
            raise VKError(message, code)

        return data.get("response")

    async def get_long_poll_server(self) -> tuple[str, str, int]:
        response = await self.call(
            "groups.getLongPollServer",
            group_id=self._group_id,
        )
        if not isinstance(response, dict):
            raise VKError("VK не вернул параметры Long Poll.")
        server = str(response.get("server") or "")
        key = str(response.get("key") or "")
        ts = int(response.get("ts") or 0)
        if not server or not key or not ts:
            raise VKError("Long Poll не настроен для сообщества.")
        return server, key, ts

    async def poll(self, server: str, key: str, ts: int, wait: int = 25) -> dict:
        try:
            response = await self._client.get(
                server,
                params={"act": "a_check", "key": key, "ts": ts, "wait": wait},
                timeout=wait + 15,
            )
        except httpx.HTTPError as exc:
            raise VKError("Long Poll прервался. Переподключаюсь.") from exc
        if response.status_code >= 400:
            raise VKError(f"Long Poll вернул HTTP {response.status_code}.")
        try:
            return response.json()
        except ValueError as exc:
            raise VKError("Long Poll вернул некорректный ответ.") from exc

    async def get_user(self, user_id: int) -> dict[str, Any]:
        response = await self.call(
            "users.get",
            user_ids=user_id,
            fields="screen_name,first_name,last_name",
        )
        if isinstance(response, list) and response:
            return response[0]
        return {}

    async def send_message(
        self,
        peer_id: int,
        text: str,
        *,
        keyboard: str | None = None,
        dont_parse_links: bool = False,
    ) -> int | None:
        params: dict[str, Any] = {
            "peer_id": peer_id,
            "random_id": secrets.randbelow(2_000_000_000),
            "message": text[:4096],
            "dont_parse_links": int(dont_parse_links),
        }
        if keyboard:
            params["keyboard"] = keyboard
        response = await self.call("messages.send", **params)
        return int(response) if isinstance(response, int) else None

    async def set_typing(self, peer_id: int) -> None:
        try:
            await self.call("messages.setActivity", peer_id=peer_id, type="typing")
        except VKError:
            # Индикатор набора не критичен.
            pass
