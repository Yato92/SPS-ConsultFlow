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
    prototype_url: str = "http://127.0.0.1:5173/prototype/"
    notifications_interval: int = 5
    request_timeout: int = 20

    ai_enabled: bool = True
    polza_api_key: str = ""
    polza_base_url: str = "https://polza.ai/api/v1"
    ai_model: str = "openai/gpt-4o-mini"
    ai_temperature: float = 0.4
    ai_max_tokens: int = 1200
    ai_timeout: float = 90.0
    ai_history_limit: int = 12
    ai_extra_prompt: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token) and ":" in self.bot_token and "PUT-YOUR" not in self.bot_token

    @property
    def is_ai_configured(self) -> bool:
        return self.ai_enabled and bool(self.polza_api_key.strip())


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()
