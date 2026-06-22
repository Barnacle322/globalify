# Phase 4 — Paddle Billing + Entitlement + Ads (mock-now, flip-live)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Monetization — a real Pro entitlement on the user (replacing the `viewer_is_pro=False` hardcode), a `/pricing` page, Paddle Billing (Pro ~$7/mo + one-time lifetime) driven by a **signature-verified, idempotent webhook**, and ad slots for the free tier — all **env-gated** so the suite/dev/CI run without a Paddle account.

**Architecture:** Entitlement lives on `UserPayment` (`is_pro`/`pro_source`/`pro_expires_at` + Paddle ids); `current_user.is_pro` gates Pro features. Paddle is the merchant of record — **webhooks are the source of truth** (not the JS callback): verify the `Paddle-Signature` HMAC over the RAW body, dedupe on `event_id`, map `transaction.completed`(lifetime)/`subscription.created|activated|updated|canceled` → entitlement. `/pricing` opens Paddle.js checkout with `customData.user_id`. Ads render to non-Pro users only. Design reference: master spec **§5** + `docs/pivot-research.md` **§5** (Paddle Billing). Python ≥3.11 is satisfied (3.14).

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never `main`.
- **Env-gated:** no hard Paddle dependency — `paddle_is_configured` gates checkout + webhook processing; `/pricing` renders without Paddle (checkout button only when configured); the suite passes with NO `_PADDLE_*`. Ads gated by a config flag.
- **Webhook security (non-negotiable — the old Stripe webhook was fragile):** verify the `Paddle-Signature` HMAC over the UNMODIFIED raw request body BEFORE parsing; reject (400) if no/invalid signature when a secret is configured; CSRF-exempt the webhook; idempotent on `event_id`; return non-2xx on handler error so Paddle retries. Entitlement is granted ONLY from a verified webhook, never the client callback.
- **Entitlement source of truth:** `UserPayment` columns; `current_user.is_pro` derived (active subscription OR lifetime OR `pro_expires_at` in future).
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run pytest` green (no Paddle creds); `uv run ruff check . && uv run ruff format --check .` clean; app imports + `db.create_all`.
- **Commits:** conventional subject; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: Entitlement model + Pro gating + `/pricing`

**Files:** `models/user.py` (`UserPayment` entitlement fields + `User.is_pro`), Alembic revision, `routes/public.py` (replace `viewer_is_pro=False`), `routes/payment.py` (new, or reuse) + `templates/pricing.html`, `tests/test_entitlement.py`.

- [ ] **Step 1:** Extend `UserPayment` (read current fields first; it has a `Tier` enum): add `is_pro: bool=False`, `pro_source: str|None` (subscription|lifetime), `pro_expires_at: datetime|None`, `paddle_customer_id: str|None`, `paddle_subscription_id: str|None`. Add `User.is_pro` property → `user_payment is not None and (user_payment.is_pro and (pro_expires_at is None or pro_expires_at > now))`. Helper `UserPayment.grant_pro(source, expires_at=None)` / `revoke_pro()`. Alembic revision (chain off head).
- [ ] **Step 2:** Replace `viewer_is_pro = False` in `public.py`'s profile routes with `viewer_is_pro = current_user.is_authenticated and current_user.is_pro`. (Pro-gated contact now actually unlocks for Pro users — the template already branches on `viewer_is_pro`.)
- [ ] **Step 3:** `/pricing` route + `templates/pricing.html` (extends base): Free vs Pro comparison (per spec §3: no ads, advanced filters, saved searches, alerts, CSV export, full contacts), the ~$7/mo + lifetime options. A "Go Pro" button that opens Paddle checkout — render the button ONLY `{% if paddle_is_configured %}` (else a "coming soon" / waitlist state). This fixes the gated-contact CTA that currently 404s on `/pricing`.
- [ ] **Step 4:** `tests/test_entitlement.py`: `User.is_pro` false by default; `grant_pro("lifetime")` → true; `grant_pro("subscription", expires=future)` → true, past-expiry → false; a Pro user GET on a profile sees contact in the DOM, a non-Pro does not (render assertion); `/pricing` renders 200 with + without Paddle config.
- [ ] **Step 5: Gate. Commit** (`feat(billing): Pro entitlement on UserPayment + /pricing; wire real Pro gating`).

---

## Task 2: Paddle Billing — checkout + signature-verified webhook

**Files:** `pyproject.toml` (+`paddle-billing` / `paddle-python-sdk` — pick the maintained one; if neither installs cleanly, implement REST + manual HMAC), `config.py` (Paddle settings), `utils/paddle.py` (signature verify + event handlers), `routes/payment.py` (`/payment/webhook`, checkout init), `templates/pricing.html` (Paddle.js), `tests/test_paddle_webhook.py`.

- [ ] **Step 1:** Add the Paddle SDK (`uv add paddle-billing` or the maintained `paddle-python-sdk`; if it won't resolve, do REST via `requests` + manual `hmac`/`hashlib` — and note it). config: `paddle_api_key`, `paddle_client_token`, `paddle_webhook_secret`, `paddle_price_monthly`, `paddle_price_lifetime`, `paddle_environment` (sandbox|production) — `str|None`, `_PADDLE_*` aliases + `paddle_is_configured` (api_key + webhook_secret present).
- [ ] **Step 2:** `utils/paddle.py`: `verify_signature(raw_body: bytes, sig_header: str) -> bool` per Paddle: header `ts=<unix>;h1=<hex>`, `signed = ts + ':' + raw_body`, HMAC-SHA256 with `paddle_webhook_secret`, timing-safe compare, reject drift > tolerance (~5s, configurable). `handle_event(event: dict)`: dispatch on `event_type` — `transaction.completed` (if items include the lifetime price → `grant_pro(user, "lifetime")` by `customData.user_id`), `subscription.created`/`activated` (store customer/subscription id + `grant_pro("subscription", current_period_end)`), `subscription.updated` (reconcile expiry/state), `subscription.canceled` (set expiry = period end / `revoke_pro` at period end). Idempotent: dedupe by `event_id` (a tiny `processed_webhook(event_id)` table or a set check).
- [ ] **Step 3:** `routes/payment.py`: `POST /payment/webhook` (`@csrf.exempt`) — read `request.get_data()` (RAW) FIRST; if `paddle_is_configured`: `verify_signature(...)` → 400 on fail; parse + `handle_event`; return 200 on success, **non-2xx on handler error** (so Paddle retries). If NOT configured: log + 200 no-op (so a stray request doesn't error). A checkout-init endpoint/context that passes the price id + `customData={user_id}` to Paddle.js.
- [ ] **Step 4:** `templates/pricing.html`: include Paddle.js (`cdn.paddle.com/paddle/v2/paddle.js`) + `Paddle.Initialize({token})` + a `Paddle.Checkout.open({items:[{priceId}], customData:{user_id}})` on the Go-Pro button — ONLY `{% if paddle_is_configured %}`.
- [ ] **Step 5:** `tests/test_paddle_webhook.py` (mocked, no network): `verify_signature` accepts a correctly-HMAC'd body + rejects a tampered body / wrong ts; `POST /payment/webhook` with a valid signed `transaction.completed` lifetime payload → user becomes Pro; an INVALID signature → 400 + NOT Pro; the same `event_id` twice → entitlement applied once (idempotent); `subscription.canceled` → expiry set. Unconfigured webhook → 200 no-op. Build the signed payloads in-test with the test secret.
- [ ] **Step 6: Gate. Commit** (`feat(billing): Paddle checkout + signature-verified idempotent webhook`).

---

## Task 3: Ads for the free tier

**Files:** `config.py` (ads flag), `templates/partials/_ad_slot.html`, browse/profile templates, `tests/`.

- [ ] **Step 1:** config: `ads_enabled: bool` (alias `_ADS_ENABLED`, default False) + optional `ads_provider`/slot ids (for later AdSense/Ezoic; house ads need no key).
- [ ] **Step 2:** `_ad_slot.html` partial — a house/sponsor ad block (a styled placeholder/sponsor card now; provider script later). Render it ONLY when `ads_enabled` AND the viewer is NOT Pro (`not (current_user.is_authenticated and current_user.is_pro)`). Place a slot on browse pages (e.g. between result rows) + profile sidebar. Expose the gating to templates via a context processor (`show_ads`).
- [ ] **Step 3:** `tests/`: a render test — with `ads_enabled` on + anonymous viewer, the ad slot appears; with a Pro viewer, it does NOT; with `ads_enabled` off, it does not.
- [ ] **Step 4: Gate. Commit** (`feat(monetization): free-tier ad slots (config-gated, hidden for Pro)`).

---

## Self-Review

**Coverage (spec §5):** entitlement + Pro gating + /pricing (T1) · Paddle checkout + secure webhook (T2) · ads (T3). Fixes the `viewer_is_pro=False` hardcode + the `/pricing` 404.

**Flip-live:** set `_PADDLE_*` (api key, webhook secret, price ids, client token) + point the Paddle dashboard webhook at `/payment/webhook`; set `_ADS_ENABLED` (+ provider) to show ads. No code change.

**Deferred:** Stripe→Paddle subscriber migration (zero existing subscribers per the owner — N/A); CSV export / saved searches / alerts Pro features (Pro entitlement now EXISTS to gate them — implement the features in a later pass); real ad-network integration (house slots now).

**Risk control:** webhook signature-verified over raw body + idempotent + grants only from verified events (closes the old Stripe-webhook fragility class); entitlement derived server-side, never from the client; everything env-gated so no Paddle account is needed to build/test; Pro gating is server-rendered (contact omitted from DOM for non-Pro, as in Phase 2b).
