"""Typed application configuration.

A single source of truth for environment-derived config. Required secrets have
no defaults, so the app fails fast at startup instead of silently falling back
to insecure values. Existing leading-underscore env var names are preserved via
field aliases.
"""

from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    PRODUCTION = "production"
    TESTING = "testing"
    DEBUG = "debug"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    env: Environment = Field(default=Environment.PRODUCTION, alias="FLASK_ENV")
    secret_key: str = Field(alias="SECRET_KEY")
    database_url: str = Field(default="sqlite:///db.sqlite", alias="_DATABASE_URL")
    sqlalchemy_pool_size: int = Field(default=5, alias="SQLALCHEMY_POOL_SIZE")
    sqlalchemy_pool_recycle: int = Field(default=1800, alias="SQLALCHEMY_POOL_RECYCLE")
    sentry_dsn: str | None = Field(default=None, alias="_SENTRY_DSN")
    resend_api_key: str | None = Field(default=None, alias="_RESEND_API_KEY")
    email_from: str = Field(default="Globalify <noreply@mail.globalify.xyz>", alias="_EMAIL_FROM")

    @property
    def is_testing(self) -> bool:
        return self.env is Environment.TESTING

    @property
    def is_debug(self) -> bool:
        return self.env is Environment.DEBUG

    @property
    def email_is_configured(self) -> bool:
        return bool(self.resend_api_key)


def get_settings() -> Settings:
    return Settings()
