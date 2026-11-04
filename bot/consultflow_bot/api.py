"""HTTP-клиент к API ConsultFlow."""

from typing import Any

import httpx


class APIError(Exception):
    """Ошибка бизнес-логики или недоступность API."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ConsultFlowAPI:
    def __init__(self, base_url: str, token: str, timeout: float = 20.0) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            headers={"X-Bot-Token": token},
            timeout=timeout,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _call(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise APIError(
                "Сервис ConsultFlow временно недоступен. Попробуйте позже."
            ) from exc

        if response.status_code >= 400:
            detail: Any
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = response.text
            if isinstance(detail, list):
                detail = "; ".join(str(item) for item in detail)
            raise APIError(
                str(detail or f"Ошибка API ({response.status_code})"),
                response.status_code,
            )
        return response.json()

    async def register(self, telegram_id: int, username: str | None, full_name: str) -> dict:
        return await self._call(
            "POST",
            "/api/bot/users",
            json={
                "telegram_id": telegram_id,
                "username": username,
                "full_name": full_name,
            },
        )

    async def create_order(self, **payload: Any) -> dict:
        return await self._call("POST", "/api/bot/orders", json=payload)

    async def my_orders(self, telegram_id: int, limit: int = 10) -> list[dict]:
        return await self._call(
            "GET", "/api/bot/orders", params={"telegram_id": telegram_id, "limit": limit}
        )

    async def order_detail(self, number: str, telegram_id: int) -> dict:
        return await self._call(
            "GET", f"/api/bot/orders/{number}", params={"telegram_id": telegram_id}
        )

    async def queue(self, telegram_id: int) -> list[dict]:
        return await self._call(
            "GET", "/api/bot/queue", params={"telegram_id": telegram_id}
        )

    async def change_status(
        self, order_id: int, telegram_id: int, status: str, comment: str | None = None
    ) -> dict:
        return await self._call(
            "POST",
            f"/api/bot/orders/{order_id}/status",
            json={"telegram_id": telegram_id, "status": status, "comment": comment},
        )

    async def stats(self, telegram_id: int) -> dict:
        return await self._call(
            "GET", "/api/bot/stats", params={"telegram_id": telegram_id}
        )

    async def dashboard_link(self, telegram_id: int) -> dict:
        return await self._call(
            "POST", "/api/bot/link", json={"telegram_id": telegram_id}
        )

    async def pricing(self) -> dict:
        return await self._call("GET", "/api/bot/pricing")

    async def pending_notifications(self, limit: int = 20) -> list[dict]:
        return await self._call(
            "GET", "/api/bot/notifications", params={"limit": limit}
        )

    async def ack_notifications(self, ids: list[int]) -> dict:
        return await self._call("POST", "/api/bot/notifications/ack", json={"ids": ids})
