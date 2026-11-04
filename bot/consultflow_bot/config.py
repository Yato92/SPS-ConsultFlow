"""Настройки Telegram-бота ConsultFlow."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = ""
    backend_url: str = "http://127.0.0.1:8000"
    bot_api_token: str = "dev-bot-token-change-me"
    notifications_interval: int = 5
    request_timeout: int = 20

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token) and ":" in self.bot_token and "PUT-YOUR" not in self.bot_token


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()
