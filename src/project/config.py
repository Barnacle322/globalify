"""Typed application configuration.

A single source of truth for environment-derived config. Required secrets have
no defaults, so the app fails fast at startup instead of silently falling back
to insecure values. Existing leading-underscore env var names are preserved via
field aliases.
"""

import os
from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    PRODUCTION = "production"
    TESTING = "testing"
    DEBUG = "debug"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # In testing, never read a developer's local .env: the suite supplies its own
        # env via conftest. Reading .env breaks hermeticity — it satisfies the fail-fast
        # SECRET_KEY check and could enable live integrations (e.g. Gemini embeddings)
        # mid-test. Other modes read .env normally.
        env_file=None if os.getenv("FLASK_ENV") == "testing" else ".env",
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
    email_from: str = Field(default="Globalify <noreply@mail.globalify.org>", alias="_EMAIL_FROM")

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
        default="Globalify Directory contact@globalify.org",
        alias="_EDGAR_USER_AGENT",
    )

    # Gemini embeddings (app-side; provider "none" disables, "gemini" enables)
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    embedding_provider: str = Field(default="none", alias="_EMBEDDING_PROVIDER")
    embedding_model: str = Field(default="gemini-embedding-001", alias="_EMBEDDING_MODEL")
    embedding_dim: int = Field(default=768, alias="_EMBEDDING_DIM")
    # Max cosine distance for a vector match. Calibrated live against gemini-embedding-001
    # (relevant matches land ~0.36-0.45); tune per corpus. 0.30 was too strict (no recall).
    embedding_distance_threshold: float = Field(default=0.55, alias="_EMBEDDING_DISTANCE_THRESHOLD")

    @property
    def embeddings_enabled(self) -> bool:
        """True when Gemini embeddings are fully configured."""
        return self.embedding_provider == "gemini" and bool(self.gemini_api_key)

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
        """True when the Cap endpoint, site key and secret are all present.

        Current Cap puts the site key in the URL path (for both the widget and
        siteverify), so the site key is required — not just endpoint + secret.
        """
        return bool(self.cap_api_endpoint and self.cap_site_key and self.cap_secret)

    @property
    def cap_site_endpoint(self) -> str | None:
        """Per-site Cap base URL ``{endpoint}/{site_key}/`` (trailing slash).

        The current Cap API addresses each site by its key in the path: the
        widget points ``data-cap-api-endpoint`` here, and server verification
        POSTs to ``{this}siteverify``.
        """
        if not (self.cap_api_endpoint and self.cap_site_key):
            return None
        return f"{self.cap_api_endpoint.rstrip('/')}/{self.cap_site_key}/"

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
