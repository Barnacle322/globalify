# Phase 0 — Modernize Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Get the dormant Globalify app booting cleanly on a modern, tested base — Python 3.14, bumped dependencies, a typed `pydantic-settings` config layer that fails fast on missing secrets (closing the forgeable-`SECRET_KEY` hole), a pytest harness, and CI — without touching the search/model code that Phase 1 rewrites.

**Architecture:** Introduce a single typed `Settings` object (`pydantic-settings`) and wire the app-core config (`SECRET_KEY`, database, env, pool, Sentry) through it, replacing scattered `os.getenv` defaults. Establish a pytest harness that neutralizes import-time network clients so the app is importable in CI. Bump the runtime and dependencies via `uv`, gated by a boot smoke test. No new product features; no Typesense upgrade; no dead-code/dead-dep removal (those belong to later phases).

**Tech Stack:** Python 3.14, Flask, Flask-SQLAlchemy/SQLAlchemy 2.0, `pydantic` + `pydantic-settings`, `uv` (project + lockfile), `granian` (prod WSGI), `pytest`, `ruff`, GitHub Actions.

## Global Constraints

- **Branch:** all work on `revamp/pivot-design` (already checked out). Do not commit to `main`.
- **Python floor:** `requires-python = ">=3.14"`. If any required dependency lacks a Python 3.14 wheel and blocks `uv lock`, fall back to `">=3.13"` and note it in the commit body.
- **Do NOT in Phase 0:** upgrade the Typesense server or client (stays v26 / client 0.21 — Phase 1 owns it); remove dead dependencies or dead code (`stripe`, `sendgrid`, `google-cloud-*`, `authlib`, `googlemaps`, Vue, OAuth — their code still exists, removed in their phases); migrate integration-specific `os.getenv` calls (OAuth/Stripe/Pub-Sub/Maps) to `Settings` — only app-core config moves now.
- **Env var naming:** preserve the existing leading-underscore env var names (`_DATABASE_URL`, `_SENTRY_DSN`, …) via pydantic field aliases so Cloud Run / `cloudbuild.yaml` env keeps working. Framework vars (`SECRET_KEY`, `FLASK_ENV`) keep their existing names.
- **Lint/format:** ruff, line-length 120, double quotes (config already in `pyproject.toml`). Every task must pass `ruff check .` and `ruff format --check .`.
- **Commits:** conventional-commit subject; end every commit message with the trailer:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## File Structure

- `tests/__init__.py` — marks the test package (new).
- `tests/conftest.py` — shared fixtures; sets dummy env + neutralizes import-time network clients; provides `app` and `client` fixtures (new).
- `tests/test_smoke.py` — app-boot regression net (new).
- `tests/test_config.py` — unit tests for the `Settings` layer (new).
- `src/project/config.py` — the typed `Settings` object + `Environment` enum + `get_settings()` (new).
- `src/project/__init__.py` — `create_app` rewired to read app-core config from `Settings`; hardcoded `SECRET_KEY` default removed (modify).
- `pyproject.toml` — `requires-python` bumped to 3.14; `granian` + `pydantic-settings` added; `[tool.pytest.ini_options]` added; deps upgraded via `uv lock --upgrade` (modify).
- `uv.lock` — regenerated (modify).
- `.python-version` — pin `3.14` (new).
- `Dockerfile` — base image → `python:3.14-slim-bookworm`; remove ad-hoc `uv pip install granian` (modify).
- `.github/workflows/ci.yml` — ruff + pytest on Python 3.14 (new).

---

## Task 1: Pytest harness + boot smoke test (safety net on current code)

Establish the test harness **before** changing dependencies, so later tasks have a regression net. The app currently constructs network clients at import (`googlemaps.Client` in `utils/suggestion.py:7` raises on a missing key; `PublisherClient.from_service_account_info` in `utils/google_helpers/google_pubsub.py:24` raises on invalid creds), so the harness sets dummy env and neutralizes the Pub/Sub constructor before importing the app.

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_smoke.py`
- Modify: `pyproject.toml` (add `[tool.pytest.ini_options]`)

**Interfaces:**
- Consumes: `project.create_app` (existing factory, signature `create_app(database_url="sqlite:///db.sqlite")`).
- Produces: pytest fixtures `app` (a testing-config Flask app) and `client` (its test client), importable by every later test module.

- [ ] **Step 1: Create the test package marker**

Create `tests/__init__.py` as an empty file.

- [ ] **Step 2: Write `tests/conftest.py`**

Create `tests/conftest.py`:

```python
"""Shared pytest fixtures.

Sets dummy environment variables and neutralizes import-time network clients
BEFORE importing the application, so the app is importable without real
credentials (matching the dormant app's import-time client construction).
"""

import os
import sys
from unittest import mock

# --- env defaults (must run before `project` is imported) ---
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("_DATABASE_URL", "sqlite:///test_db.sqlite")
os.environ.setdefault("_GOOGLE_MAPS_API_KEY", "test-maps-key")

# --- neutralize the Pub/Sub client that constructs at import with real creds ---
from google.cloud import pubsub_v1  # noqa: E402

pubsub_v1.PublisherClient.from_service_account_info = mock.MagicMock(
    return_value=mock.MagicMock()
)

import pytest  # noqa: E402


@pytest.fixture
def app():
    # import lazily so the env + patches above are in place first
    if "project" in sys.modules:
        del sys.modules["project"]
    from project import create_app

    application = create_app()
    application.config.update(TESTING=True)
    return application


@pytest.fixture
def client(app):
    return app.test_client()
```

- [ ] **Step 3: Write the boot smoke test**

Create `tests/test_smoke.py`:

```python
def test_app_boots(app):
    assert app is not None
    assert app.testing is True


def test_expected_blueprints_registered(app):
    for name in ("auth", "main", "search", "settings", "profile", "admin"):
        assert name in app.blueprints


def test_app_handles_a_request(client):
    # an unknown path should still route through the app (proves it serves)
    response = client.get("/this-path-does-not-exist")
    assert response.status_code in (404, 308)
```

- [ ] **Step 4: Register pytest config in `pyproject.toml`**

Add this block to `pyproject.toml` (after the `[tool.uv]` section):

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"
```

- [ ] **Step 5: Run the smoke test to verify it passes on the current code**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: 3 passed. (If collection fails on an import-time client other than Pub/Sub, add the matching dummy env var or `mock` patch to `conftest.py` and re-run.)

- [ ] **Step 6: Commit**

```bash
git add tests/ pyproject.toml
git commit -m "test: add pytest harness and app-boot smoke test

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: Python 3.14 + dependency overhaul

Bump the runtime to 3.14, add the two durable new dependencies (`granian`, `pydantic-settings`), and upgrade all dependencies to their latest compatible versions via `uv`. Dead dependencies are intentionally kept (their code is removed in later phases). The Task 1 smoke test is the regression gate.

**Files:**
- Modify: `pyproject.toml` (`requires-python`, add deps)
- Modify: `uv.lock` (regenerated)
- Create: `.python-version`
- Modify: `Dockerfile`

**Interfaces:**
- Consumes: the Task 1 smoke test (`uv run pytest tests/test_smoke.py`) as the boot regression gate.
- Produces: `pydantic-settings` and `granian` available as importable, locked dependencies for Tasks 3–5.

- [ ] **Step 1: Pin the Python version**

Create `.python-version` containing exactly:

```
3.14
```

- [ ] **Step 2: Set the Python floor in `pyproject.toml`**

Change the line `requires-python = ">=3.12"` to:

```toml
requires-python = ">=3.14"
```

- [ ] **Step 3: Add the new durable dependencies**

Run: `uv add granian pydantic-settings`
Expected: `pyproject.toml` gains `granian` and `pydantic-settings` under `[project.dependencies]`; `uv.lock` updates.

- [ ] **Step 4: Upgrade all dependencies to latest compatible**

Run: `uv lock --upgrade`
Expected: lock resolves successfully under Python 3.14.
If resolution fails because a dependency has no 3.14 wheel: set `requires-python = ">=3.13"`, create `.python-version` as `3.13`, re-run `uv lock --upgrade`, and record the fallback in this task's commit body.

- [ ] **Step 5: Sync the environment**

Run: `uv sync`
Expected: environment installs cleanly on the pinned Python.

- [ ] **Step 6: Update the Dockerfile**

In `Dockerfile`: change the first line to

```dockerfile
FROM python:3.14-slim-bookworm
```

and delete the line:

```dockerfile
RUN uv pip install granian
```

(granian now installs via `uv sync` from `pyproject.toml`.) Leave the rest unchanged.

- [ ] **Step 7: Verify the app still boots**

Run: `uv run pytest tests/test_smoke.py -v`
Expected: 3 passed. (If a bumped dependency breaks import, pin that single dependency to its last-working major in `pyproject.toml`, re-run `uv lock`/`uv sync`, and note it.)

- [ ] **Step 8: Verify lint/format still clean**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: no errors.

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml uv.lock .python-version Dockerfile
git commit -m "build: bump to Python 3.14, upgrade deps, add granian + pydantic-settings

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Typed config module (`Settings`)

Create the typed settings object with fail-fast required secrets. This task only creates and unit-tests the module; Task 4 wires it into `create_app`.

**Files:**
- Create: `src/project/config.py`
- Create: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure module).
- Produces:
  - `class Environment(str, Enum)` with members `PRODUCTION = "production"`, `TESTING = "testing"`, `DEBUG = "debug"`.
  - `class Settings(BaseSettings)` with fields `env: Environment`, `secret_key: str` (required, no default), `database_url: str`, `sqlalchemy_pool_size: int`, `sqlalchemy_pool_recycle: int`, `sentry_dsn: str | None`; properties `is_testing: bool`, `is_debug: bool`.
  - `def get_settings() -> Settings`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
import pytest
from pydantic import ValidationError

from project.config import Environment, Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "abc123")
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("_DATABASE_URL", "sqlite:///x.db")
    monkeypatch.setenv("SQLALCHEMY_POOL_SIZE", "7")

    settings = Settings(_env_file=None)

    assert settings.secret_key == "abc123"
    assert settings.env is Environment.TESTING
    assert settings.is_testing is True
    assert settings.database_url == "sqlite:///x.db"
    assert settings.sqlalchemy_pool_size == 7


def test_secret_key_is_required(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_database_url_has_safe_default(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "abc123")
    monkeypatch.delenv("_DATABASE_URL", raising=False)
    settings = Settings(_env_file=None)
    assert settings.database_url == "sqlite:///db.sqlite"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'project.config'`.

- [ ] **Step 3: Implement `src/project/config.py`**

Create `src/project/config.py`:

```python
"""Typed application configuration.

A single source of truth for environment-derived config. Required secrets have
no defaults, so the app fails fast at startup instead of silently falling back
to insecure values. Existing leading-underscore env var names are preserved via
field aliases.
"""

from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
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

    @property
    def is_testing(self) -> bool:
        return self.env is Environment.TESTING

    @property
    def is_debug(self) -> bool:
        return self.env is Environment.DEBUG


def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest tests/test_config.py -v`
Expected: 3 passed.

- [ ] **Step 5: Verify lint/format**

Run: `uv run ruff check src/project/config.py tests/test_config.py && uv run ruff format --check src/project/config.py tests/test_config.py`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add src/project/config.py tests/test_config.py
git commit -m "feat: add typed pydantic-settings config with fail-fast secrets

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Wire `Settings` into `create_app` (remove hardcoded SECRET_KEY)

Replace the app-core `os.getenv` reads in `create_app` with the typed `Settings`, deleting the hardcoded `SECRET_KEY` fallback. Integration-specific `os.getenv` calls (OAuth, Stripe, Pub/Sub, Maps) are intentionally left untouched — they belong to later phases.

**Files:**
- Modify: `src/project/__init__.py`
- Test: `tests/test_smoke.py` (extend with a fail-fast assertion)

**Interfaces:**
- Consumes: `project.config.get_settings`, `Settings`, `Environment` (from Task 3).
- Produces: a `create_app` whose app-core config is sourced from `Settings`; no behavioral change to integrations.

- [ ] **Step 1: Add a fail-fast test to `tests/test_smoke.py`**

Append to `tests/test_smoke.py`:

```python
import pytest
from pydantic import ValidationError


def test_create_app_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    import sys

    sys.modules.pop("project", None)
    from project import create_app

    with pytest.raises(ValidationError):
        create_app()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run pytest tests/test_smoke.py::test_create_app_requires_secret_key -v`
Expected: FAIL — currently `create_app` falls back to the hardcoded default instead of raising.

- [ ] **Step 3: Rewire `create_app` in `src/project/__init__.py`**

At the top of `create_app` (which currently begins with `sentry_sdk.init(...)` then `app = Flask(__name__)`), introduce settings and source app-core config from it. Replace this current block:

```python
    sentry_sdk.init(
        dsn=os.getenv("_SENTRY_DSN"), traces_sample_rate=0.25, profiles_sample_rate=0.1, attach_stacktrace=True
    )

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("_DATABASE_URL", database_url)
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_POOL_SIZE"] = int(os.getenv("SQLALCHEMY_POOL_SIZE", 5))
    app.config["SQLALCHEMY_POOL_RECYCLE"] = int(os.getenv("SQLALCHEMY_POOL_RECYCLE", 1800))
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    app.secret_key = os.getenv("SECRET_KEY", "18c2ff95-83a1-4998-8bee-0c6a2170497c")

    if os.getenv("FLASK_ENV") == "testing":
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test_db.sqlite"
```

with:

```python
    settings = get_settings()

    sentry_sdk.init(
        dsn=settings.sentry_dsn, traces_sample_rate=0.25, profiles_sample_rate=0.1, attach_stacktrace=True
    )

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_POOL_SIZE"] = settings.sqlalchemy_pool_size
    app.config["SQLALCHEMY_POOL_RECYCLE"] = settings.sqlalchemy_pool_recycle
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}
    app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
    app.secret_key = settings.secret_key

    if settings.is_testing:
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test_db.sqlite"
```

- [ ] **Step 4: Add the import**

In `src/project/__init__.py`, add to the local imports near `from .extensions import ...`:

```python
from .config import get_settings
```

(The `os` import remains — it is still used by the OAuth/Apple/integration code left untouched in this phase.)

- [ ] **Step 5: Run the full test suite**

Run: `uv run pytest -v`
Expected: all tests pass, including `test_create_app_requires_secret_key` and the existing smoke + config tests.

- [ ] **Step 6: Verify lint/format**

Run: `uv run ruff check . && uv run ruff format --check .`
Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add src/project/__init__.py tests/test_smoke.py
git commit -m "feat: source app-core config from Settings, remove hardcoded SECRET_KEY

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: GitHub Actions CI

Add CI that runs ruff + pytest on Python 3.14 so the now-enforceable quality tooling actually runs on every push/PR.

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `uv` project, `tests/`, ruff config — all from earlier tasks.
- Produces: a CI workflow; no code interface.

- [ ] **Step 1: Create the workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    env:
      FLASK_ENV: testing
      SECRET_KEY: ci-secret-key
      _GOOGLE_MAPS_API_KEY: ci-maps-key
    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          python-version: "3.14"

      - name: Install dependencies
        run: uv sync

      - name: Ruff lint
        run: uv run ruff check .

      - name: Ruff format check
        run: uv run ruff format --check .

      - name: Tests
        run: uv run pytest
```

- [ ] **Step 2: Validate the workflow runs locally (same commands)**

Run: `uv run ruff check . && uv run ruff format --check . && uv run pytest`
Expected: ruff clean, all tests pass. (This mirrors exactly what CI runs; if it's green locally it will be green in CI.)

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: run ruff and pytest on Python 3.14

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 4: (Optional) push the branch to trigger CI**

Run: `git push -u origin revamp/pivot-design`
Expected: the CI workflow appears on the branch. (Only if a GitHub remote + auth are configured; skip otherwise.)

---

## Self-Review

**1. Spec coverage (lean Phase 0 scope):**
- Python 3.14 + dependency overhaul → Task 2 ✅
- `pydantic-settings` typed config + fail-fast secrets (fixes `SECRET_KEY`) → Tasks 3, 4 ✅
- Pytest infrastructure → Task 1 ✅
- GitHub Actions CI (ruff + pytest) → Task 5 ✅
- `granian` pinned (durable bug from audit) → Task 2 ✅
- Deferred to Phase 1 (explicitly out of scope, per "Lean Phase 0" decision): Typesense v30/client-2.0 upgrade, reindex CLI, IDOR / country-filter / `delete_data` / `expire_all_by_user_id` fixes, dead-dep + dead-code removal. ✅ (intentional, not gaps)

**2. Placeholder scan:** No "TBD"/"handle errors"/"similar to" — every code and command step is concrete. ✅

**3. Type consistency:** `Settings`, `Environment`, `get_settings` defined in Task 3 are consumed with matching names/signatures in Task 4. Fixtures `app`/`client` defined in Task 1 are reused in Task 4's test. Env var names (`SECRET_KEY`, `_DATABASE_URL`, `_SENTRY_DSN`, `SQLALCHEMY_POOL_SIZE/RECYCLE`, `FLASK_ENV`, `_GOOGLE_MAPS_API_KEY`) are consistent across conftest, config, create_app, and CI. ✅
