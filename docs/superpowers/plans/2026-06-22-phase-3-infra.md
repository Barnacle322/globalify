# Phase 3 — Infra Integrations: Resend + R2 + Cap (mock-now, flip-live)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Build the three external-service integrations behind clean interfaces, **env-gated** so each is a graceful no-op until its credentials are configured — then going live is a config step, not a code change. Resend (transactional email, fills the magic-link send stub), Cloudflare R2 (S3-compatible image storage, fills the upload stubs), Cap (self-hosted captcha on the magic-link + claim endpoints).

**Architecture:** Each integration reads typed config from `src/project/config.py` (extend `Settings`, following the Phase 0 alias pattern). Each has a "configured?" check: when the key/endpoint is absent, Resend logs the email (current stub behavior), R2 uses a local-dev fallback (or raises a clear error), Cap skips verification (returns ok). This keeps `pytest`/CI/dev green with no creds. Design reference: **`docs/pivot-research.md` §5–6** (Resend/R2 integration) + master spec **§6–7**.

**Tech Stack:** `resend` (PyPI), `boto3` (R2 via S3 API), Cap (self-hosted, reCAPTCHA-compatible `siteverify`), Flask, pydantic-settings.

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never `main`.
- **Env-gated, fail-safe:** NO hard dependency on a live service. Each integration: if configured → use it; else → graceful fallback (Resend→log; R2→local `instance/uploads/` dev dir or clear error; Cap→skip/return ok). `pytest` + CI must pass with NO creds set.
- **Config in `Settings`:** add fields/groups to `config.py` with `_`-prefixed env aliases (match Phase 0). Never hardcode keys. A `*.is_configured` property gates each.
- **Don't break magic-link:** Resend slots INTO the existing `utils/email/send_magic_link` seam (Phase 2e). Keep the log fallback.
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run pytest` green (with NO service creds); `uv run ruff check . && uv run ruff format --check .` clean; app imports.
- **Commits:** conventional subject; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: Resend transactional email

**Files:** `pyproject.toml` (+`resend`), `src/project/config.py` (Resend settings), `src/project/utils/email/__init__.py` + `resend_client.py`, `templates/email/magic_link.html` (+ a base email layout), `routes/auth.py` (use the email render), `tests/test_email.py`.

- [ ] **Step 1:** `uv add resend`. Add to `Settings`: `resend_api_key: str | None` (alias `_RESEND_API_KEY`), `email_from: str` (alias `_EMAIL_FROM`, default `"Globalify <noreply@mail.globalify.org>"`), and an `email_is_configured` property (`bool(resend_api_key)`).
- [ ] **Step 2:** `utils/email/resend_client.py`: `send_email(to: str, subject: str, html: str) -> bool` — if `settings.email_is_configured`: set `resend.api_key`, build params, `resend.Emails.send(...)`, retry once on 429 honoring `ratelimit-reset`; else `current_app.logger.info("[email stub] to=%s subject=%s", to, subject)` and return True. Catch/log send errors (don't raise into the request).
- [ ] **Step 3:** Email templates: `templates/email/_layout.html` (simple branded HTML email shell) + `templates/email/magic_link.html` (renders the login link). Update `utils/email/send_magic_link(email, link)` to `render_template("email/magic_link.html", link=link)` → `send_email(email, "Your Globalify login link", html)`.
- [ ] **Step 4:** `tests/test_email.py`: with NO key set, `send_email` logs + returns True (caplog) and does NOT call the network; with a monkeypatched `resend.Emails.send`, `send_email` calls it with the right params; `send_magic_link` renders the template + sends. (Mock `resend` — do not hit the network.)
- [ ] **Step 5: Gate. Commit** (`feat(email): Resend transactional email (env-gated; magic-link template)`).

---

## Task 2: Cloudflare R2 image storage

**Files:** `pyproject.toml` (+`boto3`), `src/project/config.py` (R2 settings), `src/project/utils/r2/__init__.py` + `r2_storage.py`, the upload/delete stub sites (`routes/admin/user.py`, `routes/settings.py` — the `TODO(phase-3): upload via R2` stubs from Phase 1a), `tests/test_r2.py`.

- [ ] **Step 1:** `uv add boto3`. Add to `Settings`: `r2_account_id`, `r2_access_key_id`, `r2_secret_access_key`, `r2_bucket`, `r2_public_domain` (all `str | None`, `_R2_*` aliases) + an `r2_is_configured` property (all of account_id/keys/bucket present).
- [ ] **Step 2:** `utils/r2/r2_storage.py`: a lazily-constructed boto3 S3 client (`endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com"`, `region_name="auto"`). Functions: `upload_image(file_or_bytes, content_type) -> str` (process via the EXISTING Pillow pipeline if applicable — reuse what the old `google_storage` did; generate a `uuid4` key like `images/<uuid>.jpg`; `put_object`; return the KEY), `delete_object(key)`, `public_url(key) -> str` (`f"https://{r2_public_domain}/{key}"`). When `not r2_is_configured`: fall back to a local dev dir (`instance/uploads/`) writing the file + returning a local-served key/URL (add a tiny dev route to serve `instance/uploads/` OR use Flask static) so dev works without R2; document this.
- [ ] **Step 3:** Fill the upload/delete stubs in `admin/user.py` + `settings.py` to call `r2_storage.upload_image`/`delete_object`, **storing the returned KEY** (not a full URL) in the DB column, and compute the display URL via `public_url(key)` at render. (If the relevant model field doesn't exist on the new model, note it + wire the user-picture path that does exist.)
- [ ] **Step 4:** `tests/test_r2.py`: with NO R2 config, `upload_image` uses the local fallback (writes a file, returns a key) — no boto3 call; `public_url` builds the right URL from a key; with a monkeypatched/`moto`-mocked S3, `upload_image` calls `put_object` with the bucket + a uuid key. Unit-test the key→URL logic + gating without the network.
- [ ] **Step 5: Gate. Commit** (`feat(storage): Cloudflare R2 image storage (env-gated; local dev fallback)`).

---

## Task 3: Cap captcha on login + claim

**Files:** `src/project/config.py` (Cap settings), `src/project/utils/cap.py`, `routes/auth.py` (verify on `POST /login`), `routes/claim.py` (verify on claim submit), the login + claim form templates (the `<cap-widget>`), `docs/` (Cap self-host compose snippet), `tests/test_cap.py`.

- [ ] **Step 1:** Add to `Settings`: `cap_api_endpoint` (the self-hosted Cap base URL), `cap_site_key`, `cap_secret` (all `str | None`, `_CAP_*` aliases) + a `cap_is_configured` property.
- [ ] **Step 2:** `utils/cap.py`: `verify_captcha(token: str | None) -> bool` — if `not cap_is_configured`: return True (skip, so dev/test work); else POST to `f"{cap_api_endpoint}/siteverify"` with `{secret, response: token}` (reCAPTCHA-compatible), parse `success`, return it; on error/timeout log + return False (fail-closed when configured). Short timeout.
- [ ] **Step 3:** Wire it: in `POST /login` (auth.py) — before issuing the token, `if not verify_captcha(request.form.get("cap-token")): flash error + redirect`. Same on the claim submission(s) in `claim.py` (replacing the `# TODO` left from the reCAPTCHA removal). The `<cap-widget data-cap-api-endpoint=... data-cap-sitekey=...>` + the Cap script go on the login + claim forms, conditionally rendered only `{% if cap_is_configured %}` (so forms render without it in dev) — expose `cap_is_configured`/`cap_site_key`/`cap_api_endpoint` to those templates.
- [ ] **Step 4:** `docs/`: add a short "Self-hosting Cap" note + a `docker-compose` snippet (Cap Standalone container) and the env vars needed.
- [ ] **Step 5:** `tests/test_cap.py`: `verify_captcha(None)` returns True when unconfigured; with config + a monkeypatched HTTP call returning `{"success": true}` → True, `{"success": false}` → False, on exception → False; `POST /login` with Cap configured + a failing verify is rejected (no token issued). Mock the HTTP — no network.
- [ ] **Step 5: Gate. Commit** (`feat(captcha): self-hosted Cap on login + claim (env-gated)`).

---

## Self-Review

**Coverage:** Resend email (T1) · R2 storage (T2) · Cap captcha (T3) — each env-gated with a graceful fallback so the suite/CI/dev run with no creds. Deps `resend` + `boto3` added.

**Flip-live (when creds arrive):** set `_RESEND_API_KEY` + verify the sending domain; set `_R2_*` + a public custom domain; deploy Cap Standalone + set `_CAP_*`. No code change.

**Deferred:** alert/notification emails beyond magic-link (Phase 5/later); GCS→R2 data migration of any existing images (one-off script, gated); the bookmark-route test + `url_for` carry from 2e (fold in here if convenient).

**Risk control:** zero hard external dependency (every integration degrades); keys only via `Settings` (never hardcoded); Cap fails-closed when configured but fails-open (skips) when not, so it can't lock anyone out in dev; mocked tests, no network in CI.
