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

    # Cloudflare R2 image storage (all optional; gates R2 vs local-dev fallback)
    r2_account_id: str | None = Field(default=None, alias="_R2_ACCOUNT_ID")
    r2_access_key_id: str | None = Field(default=None, alias="_R2_ACCESS_KEY_ID")
    r2_secret_access_key: str | None = Field(default=None, alias="_R2_SECRET_ACCESS_KEY")
    r2_bucket: str | None = Field(default=None, alias="_R2_BUCKET")
    r2_public_domain: str | None = Field(default=None, alias="_R2_PUBLIC_DOMAIN")

    # Cap captcha (self-hosted, reCAPTCHA-compatible; all optional — gates captcha vs skip)
    cap_api_endpoint: str | None = Field(default=None, alias="_CAP_API_ENDPOINT")
    cap_site_key: str | None = Field(default=None, alias="_CAP_SITE_KEY")
    cap_secret: str | None = Field(default=None, alias="_CAP_SECRET")

    # Ads (config-gated — gates ad slots for non-Pro viewers)
    ads_enabled: bool = Field(default=False, alias="_ADS_ENABLED")

    # Paddle billing (all optional — gates payment UI vs "coming soon")
    paddle_client_token: str | None = Field(default=None, alias="_PADDLE_CLIENT_TOKEN")
    paddle_price_id_monthly: str | None = Field(default=None, alias="_PADDLE_PRICE_ID_MONTHLY")
    paddle_price_id_lifetime: str | None = Field(default=None, alias="_PADDLE_PRICE_ID_LIFETIME")
    paddle_api_key: str | None = Field(default=None, alias="_PADDLE_API_KEY")
    paddle_webhook_secret: str | None = Field(default=None, alias="_PADDLE_WEBHOOK_SECRET")
    paddle_environment: str = Field(default="sandbox", alias="_PADDLE_ENVIRONMENT")

    # SEC EDGAR — polite identified User-Agent (required by SEC fair-access policy)
    edgar_user_agent: str = Field(
        default="Globalify Directory contact@globalify.xyz",
        alias="_EDGAR_USER_AGENT",
    )

    @property
    def is_testing(self) -> bool:
        return self.env is Environment.TESTING

    @property
    def is_debug(self) -> bool:
        return self.env is Environment.DEBUG

    @property
    def email_is_configured(self) -> bool:
        return bool(self.resend_api_key)

    @property
    def r2_is_configured(self) -> bool:
        """True when all required R2 credentials are present."""
        return bool(self.r2_account_id and self.r2_access_key_id and self.r2_secret_access_key and self.r2_bucket)

    @property
    def cap_is_configured(self) -> bool:
        """True when the Cap endpoint and secret are both present."""
        return bool(self.cap_api_endpoint and self.cap_secret)

    @property
    def paddle_is_configured(self) -> bool:
        """True when Paddle client token, webhook secret, and at least one price ID are present."""
        return bool(
            self.paddle_client_token
            and self.paddle_webhook_secret
            and (self.paddle_price_id_monthly or self.paddle_price_id_lifetime)
        )

    @property
    def paddle_webhook_is_configured(self) -> bool:
        """True when the Paddle webhook secret is set (enables signature verification)."""
        return bool(self.paddle_webhook_secret)


def get_settings() -> Settings:
    return Settings()
