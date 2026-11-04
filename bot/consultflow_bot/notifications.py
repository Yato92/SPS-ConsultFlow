"""Фоновая доставка уведомлений из очереди API в Telegram."""

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from consultflow_bot.api import APIError, ConsultFlowAPI

logger = logging.getLogger(__name__)


async def notification_worker(
    bot: Bot, api: ConsultFlowAPI, interval: float = 5.0
) -> None:
    """Каждые N секунд забирает pending-уведомления и отправляет их в Telegram."""
    await asyncio.sleep(2)
    while True:
        try:
            items = await api.pending_notifications(limit=20)
            if items:
                sent: list[int] = []
                for item in items:
                    try:
                        await bot.send_message(
                            int(item["recipient"]),
                            item["text"],
                            disable_web_page_preview=True,
                        )
                    except (TelegramAPIError, ValueError, TypeError) as exc:
                        logger.warning(
                            "Уведомление %s не доставлено: %s", item["id"], exc
                        )
                    sent.append(int(item["id"]))
                if sent:
                    await api.ack_notifications(sent)
                    logger.info("Доставлено уведомлений: %s", len(sent))
        except asyncio.CancelledError:
            raise
        except APIError as exc:
            logger.warning("API недоступен: %s", exc)
        except Exception:  # noqa: BLE001 - цикл не должен падать
            logger.exception("Ошибка в цикле уведомлений")
        await asyncio.sleep(interval)
