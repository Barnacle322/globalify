# Phase 2e — htmx Progressive Enhancement + Magic-Link Auth

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Layer htmx progressive enhancement over the SSR baseline (live filtering, bookmark toggle) and replace the (already-OAuth-stripped) auth with passwordless **magic-link email** login — closing out Phase 2's front-end.

**Architecture:** Self-hosted htmx (~14KB, no CDN) enhances plain `<form method=get>` filters (the same Jinja partial serves full page + `#results` fragment via the `HX-Request` header) and a `hx-post` bookmark toggle keyed on Person/Org ids. Magic-link auth uses a stateful `login_tokens` table (`sha256(token)`, purpose, expiry, consumed) — request emails a verify link (email send is a stub/log until Resend lands in Phase 3), the verify route logs the user in via Flask-Login. Design reference: **`docs/phase-2-planning-brief.md` §1 (2e), §5**.

**Tech Stack:** Flask SSR + htmx (self-hosted), Flask-Login, SQLAlchemy/Alembic, `secrets`/`hashlib`, Playwright.

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never `main`.
- **Progressive enhancement:** every interaction must work with JS OFF — htmx only enhances. Filters are a real `<form method=get>`; bookmark is a real POST form fallback. Content stays server-rendered + crawlable.
- **No CDN JS:** self-host `static/vendor/htmx.min.js`, `defer`. No Vue.
- **Magic-link is stateful:** `login_tokens` stores `sha256(token)` (never the raw token), `user_id`, `purpose` (login/claim/etc.), `expires_at`, `consumed_at`. Verify is single-use + expiry-checked. Email SEND is a stub for now (log the link / a no-op `send_magic_link` that Phase 3's Resend fills) — do not block on an email provider. Note where Cap captcha attaches to the send endpoint (built in Phase 3).
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run pytest` green; `uv run ruff check . && uv run ruff format --check .` clean; app imports + `db.create_all`. Playwright where stated.
- **Commits:** conventional subject; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: htmx progressive enhancement (filters + bookmarks) + cleanup

**Files:** `static/vendor/htmx.min.js` (vendored), `templates/layouts/base.html` (include htmx in `{% block scripts %}` default), `templates/browse/list.html` (filter form + `#results` fragment), `routes/public.py` (HX-Request fragment handling), a bookmark route + `templates/partials/_bookmark_button.html`, `routes/main.py`/`search.py` (the deferred `/search`→`/investors` + `/search/investment-firms`→`/firms` 301s, now that legacy search routes can retire), dead template JS cleanup.

- [ ] **Step 1:** Vendor `htmx.min.js` into `static/vendor/`; include it `defer` in `base.html` (a `{% block scripts %}` default or the head). Confirm it's a local file, not CDN.
- [ ] **Step 2:** Filter form in `browse/list.html`: a `<form method="get" hx-get hx-target="#results" hx-push-url="true">` over the existing filter params (q, stage/industry/geo/lead_pref/etc.); results in `<div id="results">`. In `public.py`'s browse + facet handlers, when `request.headers.get("HX-Request")`, render ONLY the results fragment (a `browse/_results.html` partial that `list.html` also includes) instead of the full page. JS-off: the plain GET form still works (full-page reload).
- [ ] **Step 3:** Bookmark toggle: a `_bookmark_button.html` partial (`<form hx-post="/bookmarks/<entity_type>/<entity_id>" hx-swap="outerHTML">` with CSRF via a hidden token or `hx-headers`); a `POST /bookmarks/<entity_type>/<entity_id>` route (login_required) that toggles an `EntityBookmark` (re-keyed on Person/Org ids — confirm `EntityBookmark.exists`/add/remove API) and returns the re-rendered button partial. JS-off: it's a real form POST that redirects back. Add the button to profile + card templates.
- [ ] **Step 4:** Deferred 301s: now retire/redirect the legacy `/search` → `/investors` and `/search/investment-firms` → `/firms` (preserve query string). Resolve the route-conflict cleanly (the old `search.investor_search`/`search_investment_firms` endpoints are being replaced — repoint or redirect; if other code `url_for`s them, update or keep a redirect endpoint). Keep the JSON typeahead endpoint if still used.
- [ ] **Step 5:** Remove dead template JS: strip leftover `handleInvestorBookmark`/Vue-era `@click`/`v-if` and dead `<script>` refs from surviving templates (grep `templates/` for `v-if`, `@click`, `handleInvestor`, deleted script srcs). Regenerate `main.css`.
- [ ] **Step 6: Gate** (pytest green incl. `test_no_url_for_to_unregistered_endpoints`, `test_authenticated_pages`; ruff; import; `npm run build:css`).
- [ ] **Step 7: Playwright verify** (seed + Docker Typesense): on `/investors`, submit a filter and assert the URL updates + `#results` swaps (htmx `HX-Request` in network) AND a JS-disabled pass shows full-page results; bookmark toggle as a logged-in user returns the toggled partial; 0 console errors. Tear down. (If logged-in bookmark is hard to seed, verify the filter htmx + JS-off path.)
- [ ] **Step 8: Commit** (`feat(ui): htmx filter live-results + bookmark toggle; legacy /search 301s; JS cleanup`).

---

## Task 2: Magic-link email auth

**Files:** `models/auth_token.py` (or add to `user.py`) — `LoginToken` model + Alembic revision; `routes/auth.py` (request + verify routes, strip OAuth remnants); `templates/auth/login.html` + `verify_email.html` (reshape to magic-link); delete `templates/settings/delete_oauth_account.html`; a `utils/email/` stub `send_magic_link(...)`; `tests/test_auth_magiclink.py`.

- [ ] **Step 1:** `LoginToken` model: `id`, `user_id` FK (nullable — for signup-by-email the user may be created on verify, or create the user on request; pick one and document), `token_hash` (sha256 of a `secrets.token_urlsafe(32)`), `purpose` (str: "login"), `expires_at`, `consumed_at` (nullable). Helpers: `create_for_email(email, purpose)` → (raw_token, instance), `verify_and_consume(raw_token, purpose)` → User|None (checks unexpired + unconsumed, marks consumed). Alembic revision (chain off head) creating the table.
- [ ] **Step 2:** `send_magic_link(email, link)` stub in `utils/email/` — for now `current_app.logger.info(f"magic link for {email}: {link}")` (and a TODO to send via Resend in Phase 3). Return nothing/ok.
- [ ] **Step 3:** Auth routes in `auth.py`:
  - `GET /login` → render `auth/login.html` (just an email field; NO OAuth buttons).
  - `POST /login` → look up or create the `User` by email; mint a login token; build the absolute verify URL (`url_for("auth.verify", token=raw, _external=True)`); `send_magic_link(email, url)`; flash "check your email" (use the existing `Status` query-param flash pattern). (Cap captcha attaches here in Phase 3 — leave a `# TODO(phase-3): Cap verify` marker.)
  - `GET /auth/verify?token=...` → `LoginToken.verify_and_consume(token, "login")` → if valid `login_user(user)` + redirect to next/home; else flash an error.
  - Keep `logout`. Remove any remaining OAuth route/helper stubs.
- [ ] **Step 4:** `auth/login.html` + `verify_email.html`: reshape onto `base.html` (or the auth layout), email-only login form, remove OAuth. Delete `templates/settings/delete_oauth_account.html` and repoint the settings delete-account flow to a generic confirm (or the existing account-deletion handler) — fix any `render_template`/`url_for` to it.
- [ ] **Step 5:** `tests/test_auth_magiclink.py`: token create→verify→consume happy path; expired token rejected; already-consumed token rejected; wrong-purpose rejected; the `POST /login` route creates a token + calls the send stub (assert via caplog or a monkeypatched stub); the `GET /auth/verify` with a valid token logs the user in (session has `_user_id`). Write tests first where practical.
- [ ] **Step 6: Gate** (pytest green incl. `test_db_metadata_creates_all_tables`, `test_no_url_for_to_unregistered_endpoints`, `test_authenticated_pages`; ruff; import).
- [ ] **Step 7: Playwright verify:** `GET /login` renders the email form (no OAuth buttons), 0 console errors, has the base nav/footer. (Full link-click flow is exercised by the pytest tests since email is stubbed.)
- [ ] **Step 8: Commit** (`feat(auth): passwordless magic-link login (stateful tokens); remove OAuth remnants`).

---

## Self-Review

**Coverage (brief §1 2e, §5):** htmx asset + filter live-results + bookmark toggle (T1) · legacy /search 301s + JS cleanup (T1) · magic-link auth + token model + OAuth-remnant removal (T2). 

**Deferred:** Cap captcha on the magic-link send endpoint (Phase 3, marker left); real email send via Resend (Phase 3 — stub logs the link now); claim flow rebind onto Person/Org (Phase 5); Alpine (not needed — htmx + the tiny menu.js cover it).

**Risk control:** every enhancement degrades gracefully (JS-off forms work; content server-rendered); the magic-link token is hashed-at-rest, single-use, expiry-checked; email is stubbed so no external dependency blocks the build; new auth tests + the existing authenticated-page smoke tests guard regressions. After 2e the whole Phase 2 front-end is coherent.
