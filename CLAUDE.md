# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Globalify is a Flask directory of investors and investment firms. PostgreSQL/SQLAlchemy is the source of truth (sqlite locally), Typesense is a derived search index over a single `entities` collection, with optional app-side Gemini embeddings for hybrid search. Pages are server-rendered Jinja templates progressively enhanced with htmx (vendored, loaded per-page — no SPA framework, no bundler), styled with TailwindCSS compiled via PostCSS. Python 3.14+, package under `src/project/`, importable as `project`.

Auth is passwordless magic-link email login. Billing is Paddle. Email is Resend. Image storage is Cloudflare R2. Captcha is self-hosted Cap. Every integration is env-gated and degrades to a local stub when its env vars are absent, so the app runs with no credentials in dev/CI.

## Commands

Python is managed with `uv` (`uv venv`, `uv sync`); a `.env` file provides config (`SECRET_KEY` is required and fails fast).

```bash
# Run the app (sources .env, activates venv, flask run on :5000)
source start.sh

# Tailwind watcher (separate terminal during dev) / one-shot build
npm run css
npm run build:css

# Format HTML (Prettier + tailwindcss plugin)
npm run html

# Lint / format Python (pre-commit hook runs both)
ruff check . --fix
ruff format .

# Tests (hermetic: .env NOT read, sqlite, all integrations stubbed)
uv run pytest

# DESTRUCTIVE: drop+create DB, seed demo entities + admin users, rebuild Typesense
flask setup

# Non-destructive Typesense reindex of the entities collection
flask reindex

# Run a data collector (registry: sample, edgar)
flask collect <source> [--limit 50] [--dry-run]
```

Run Typesense locally with Docker (required for search):

```bash
docker run --name typesense -p 8108:8108 -v $(pwd)/typesense-data:/data \
  typesense/typesense:30.0 --data-dir /data --api-key=xyz --enable-cors
```

## Architecture

**App factory** — `src/project/__init__.py` defines `create_app()` and exports `application` (WSGI entrypoint; production serves via granian behind ProxyFix). All blueprints, error handlers, CLI commands (`setup`, `reindex`, `collect`), and context processors (Cap config, Paddle config, `show_ads`) are registered here.

**Config** — `src/project/config.py` is a pydantic-settings `Settings` class behind `get_settings()`. Env vars use leading-underscore aliases (`_DATABASE_URL`, `_RESEND_API_KEY`, `_PADDLE_*`, `_R2_*`, `_CAP_*`, `_EMBEDDING_*`, `GEMINI_API_KEY`). Each integration has an `*_is_configured` property; unset means stub/skip mode. `FLASK_ENV=testing` skips `.env` entirely.

**Extensions** — `src/project/extensions.py` holds the shared singletons (`db`, `login_manager`, `migrate`, `csrf`). Import these rather than re-instantiating. Models use `DeclarativeBase` + typed `Mapped[...]` columns with `MappedAsDataclass`.

**Blueprints** (`src/project/routes/`): `auth`, `main`, `sitemap`, `claim`, `public` (SSR profiles + browse: `/investors`, `/firms`), `search` (typeahead JSON) — all unprefixed; `settings` under `/settings`; `admin` under `/admin` (split under `routes/admin/`); `payment` under `/payment` (Paddle webhook).

**Models** (`src/project/models/`, re-exported from `__init__.py`) — the entity layer is polymorphic over `(entity_type: EntityType, entity_id)`: `Person`, `Organization`, `InvestorProfile`, `Affiliation`, `Geography`, plus `Entity*` join tables (industries, stages, geographies, bookmarks). User layer: `User`/`UserInfo`/`UserPayment` (Pro entitlement), `LoginToken` (magic links, sha256-hashed, single-use), `EmailVerification` (legacy), `ClaimRequest`/`ClaimVerification`, `ProcessedWebhook` (Paddle idempotency). Collector provenance lives on `Person`/`Organization` (`source`, `source_id`, `last_synced_at`) with `upsert_from_source` (never clobbers claimed/human-edited rows).

**Search (Typesense)** — `models/entity_search.py` owns the dual-store pattern: `sync_search_index(recreate=False)` rebuilds the `entities` collection, `sync_one(entity_type, id)` upserts one doc after writes, `delete_data` removes one, `get_search` queries. `_build_entity_doc()` is the single source of document construction; after changing searchable fields update it and the schema together, then `flask reindex`. Embeddings are generated app-side via Gemini (`utils/embeddings/`, model `gemini-embedding-001`, L2-normalized) only when `_EMBEDDING_PROVIDER=gemini` + `GEMINI_API_KEY` are set; search falls back to keyword-only otherwise.

**Auth (magic link)** — `routes/auth.py`: `POST /login` finds-or-creates the User (+`UserInfo`+`UserPayment`), verifies Cap captcha, issues a 30-min single-use `LoginToken`, emails the link via Resend. `GET /auth/verify?token=…` consumes it, sets `is_verified=True` (the click IS verification), logs in; only safe relative `next` is honored. A legacy `EmailVerification` code flow remains for pre-migration accounts.

**Collectors** (`src/project/collectors/`) — `base.py` defines `Collector` (fetch → parse → `NormalizedRecord` → idempotent upsert + Typesense sync) and `REGISTRY`. `edgar.py` pulls SEC EDGAR Form D issuers (identified User-Agent required by SEC, `_EDGAR_USER_AGENT`). Fixture-tested, no network in tests.

**Billing (Paddle)** — `routes/payment.py` webhook: raw-body HMAC signature check (`utils/paddle.py`), idempotency via `ProcessedWebhook`, grants/revokes Pro on `UserPayment`. Ads render only when `_ADS_ENABLED` and the user is not Pro (`partials/_ad_slot.html`).

**Frontend** — Jinja templates in `src/project/templates/` extend `layouts/` (`base`, `layout_admin`, `layout_auth`, `layout_clean`, `layout_error`). htmx v1.9 is vendored at `static/vendor/htmx.min.js` and loaded per-page where used (e.g. browse filters, bookmark buttons). CSS compiles from `static/src/input.css` to `static/css/main.css`. Fonts: Poppins, Fraunces, Space Mono (self-hosted). Design system: "The Ledger".

**Other integrations** — Sentry (errors), PostHog (server-side `utils/posthog.py` + inline snippet), R2 via boto3 (`utils/r2/`, dev fallback serves `/uploads/<filename>` from `instance/uploads/` when unconfigured), Resend (`utils/email/`, logs a stub line when keyless).

## Conventions

- **Python style**: ruff, line-length 120, double quotes, rules `E,F,W,B,Q,I,N,UP`; `migrations/` excluded. Pre-commit runs ruff lint + format.
- **Testing**: `tests/conftest.py` forces `FLASK_ENV=testing` + `sqlite:///test_db.sqlite` before importing `project`; CSRF disabled; all external services stubbed — tests need no Docker/credentials. TDD is the norm here (tests are written first).
- **Migrations**: Flask-Migrate/Alembic in `migrations/`. `flask setup` is destructive — never run it against real data; use `flask db upgrade` + `flask reindex`.
- **Datetimes**: `pro_expires_at` is naive UTC; entity `last_synced_at` is tz-aware — match the column's convention, use `datetime.now(datetime.UTC)` (never deprecated `utcnow()`).
- **JS/HTML formatting**: Prettier via `npm run html`.
- **Docs**: `docs/codebase-map.md` and `docs/*.md` describe the pivot and deployment (docker-compose + granian); the README predates the pivot — trust `docs/` over README.
