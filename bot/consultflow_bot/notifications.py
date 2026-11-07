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
                sent = 0
                failed = 0
                for item in items:
                    try:
                        recipient = int(item["recipient"])
                    except (ValueError, TypeError):
                        continue
                    if recipient < 0:
                        # Отрицательные ID — пользователи VK-бота.
                        continue
                    try:
                        await bot.send_message(
                            recipient,
                            item["text"],
                            disable_web_page_preview=True,
                        )
                        # Подтверждаем сразу, чтобы не отправить повторно.
                        await api.ack_notifications([int(item["id"])])
                        sent += 1
                    except (TelegramAPIError, ValueError, TypeError) as exc:
                        logger.warning(
                            "Уведомление %s не доставлено: %s", item["id"], exc
                        )
                        try:
                            await api.fail_notifications([int(item["id"])])
                            failed += 1
                        except (APIError, ValueError, TypeError):
                            pass
                if sent:
                    logger.info("Доставлено уведомлений: %s", sent)
                if failed:
                    logger.info("Не доставлено уведомлений: %s", failed)
        except asyncio.CancelledError:
            raise
        except APIError as exc:
            logger.warning("API недоступен: %s", exc)
        except Exception:  # noqa: BLE001 - цикл не должен падать
            logger.exception("Ошибка в цикле уведомлений")
        await asyncio.sleep(interval)
