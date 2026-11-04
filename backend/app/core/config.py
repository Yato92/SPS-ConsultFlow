"""Конфигурация приложения ConsultFlow."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "ConsultFlow API"
    environment: str = "development"
    api_prefix: str = "/api"

    secret_key: str = "consultflow-dev-secret-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    magic_link_expire_minutes: int = 15
    # Ссылка клиента на личный кабинет из VK/Telegram-бота.
    client_link_expire_minutes: int = 10080

    database_url: str = "sqlite:///./consultflow.db"

    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8050"
    )
    frontend_url: str = "http://localhost:5173"
    seed_demo: bool = True
    # Публичный демонстрационный API для учебного прототипа (без production-данных).
    prototype_demo: bool = True

    bot_api_token: str = "dev-bot-token-change-me"
    manager_telegram_ids: str = ""
    manager_vk_ids: str = ""

    # ИИ-разбор заявок (BPMN: извлечение данных, классификация, КП).
    ai_enabled: bool = True
    polza_api_key: str = ""
    polza_base_url: str = "https://polza.ai/api/v1"
    ai_model: str = "deepseek/deepseek-v4.1-flash-1017"
    ai_temperature: float = 0.2
    ai_max_tokens: int = 900
    ai_timeout: float = 60.0

    admin_email: str = "admin@consultflow.ru"
    admin_password: str = "admin12345"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def manager_ids(self) -> set[int]:
        result: set[int] = set()
        for chunk in self.manager_telegram_ids.split(","):
            chunk = chunk.strip()
            if chunk.lstrip("-").isdigit():
                result.add(int(chunk))
        return result

    @property
    def manager_vk_id_set(self) -> set[int]:
        result: set[int] = set()
        for chunk in self.manager_vk_ids.split(","):
            chunk = chunk.strip()
            if chunk.isdigit():
                result.add(int(chunk))
        return result

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def is_ai_configured(self) -> bool:
        return self.ai_enabled and bool(self.polza_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
