# Globalify — System Map & Revival Plan

*Prepared for the owner and incoming developers reviving a dormant (since ~Apr 2025) Flask investor/startup discovery platform. Synthesized from 12 parallel subsystem explorations of the `globalify` codebase.*

> **Verification note (2026-06-22).** The CRITICAL findings were spot-checked against source after synthesis:
> - ✅ **Forgeable `SECRET_KEY`** — confirmed: hardcoded UUID fallback in `__init__.py`; `cloudbuild.yaml` does not pass `SECRET_KEY`. Verify it's set on the Cloud Run service directly.
> - ✅ **Open CRUD on investments (IDOR)** — confirmed: `investment.py` routes have no ownership/admin check; any verified user can edit/delete any investment by id.
> - ❌ **"Spoofable Stripe billing" — CORRECTED.** When `_STRIPE_WEBHOOK_SECRET` is unset, `event` stays `None` and the handler returns `"Event not found"` *before* the `match`, so the unsigned path is **inert (fail-closed), not exploitable**. The real issue is reliability (webhooks silently no-op without the secret) + confusing dead control flow. Reclassified below as HIGH, not CRITICAL.
> - Other findings (search filter bugs, auth-provider breakage, blocking calls, duplication) were reported by explorers but not all independently re-verified — treat HIGH/MEDIUM items as leads to confirm before acting.

---

## 1. Executive Summary

**Globalify** is a Flask 3 web application that pairs entrepreneurs with investors. It runs two parallel worlds that meet through a search index:

- **A curated catalog** of `Investor`s (individuals) and `InvestmentFirm`s (funds), largely seeded from pre-scraped CSV/JSONL files, enriched with industries, rounds, notable investments, geolocation, and check-size ranges.
- **A platform-user side** where authenticated `User`s build `Company` profiles, log `FundingRound`s and `Investment`s, bookmark catalog entities, and subscribe to a paid tier for unlocking contact details.

The two are bridged by **Typesense**, a derived full-text + vector search index that mirrors Postgres (the source of truth) and powers the core product surface: searching, filtering, faceting, and semantic ranking of investors/firms/companies.

### Core user journeys

- **Entrepreneur path:** OAuth login → onboarding (`/onboarding/basic`) → email verification → create a `Company`, add team members (`UserCompany` with roles), record funding rounds/investments → search the investor catalog → bookmark/contact (gated by payment).
- **Investor path:** OAuth login → investor onboarding (`/onboarding/investor`) creates an `Investor` profile → toggles `is_investor_mode_active` to see a company-centric search instead.
- **Claiming:** A logged-in user claims an existing scraped `Investor` profile via either a **manual** path (reCAPTCHA + `ClaimRequest` for admin review) or an **email-token** path (`ClaimVerification` mailed to the profile's on-file address). On success, `investor.user_id` is bound to the user and a snapshot (`InvestorOriginPoint`) is preserved.
- **Search:** Public/auth search pages call `Model.get_search()` → builds a Typesense `SearchBuilder` query (keyword + optional vector) → returns plain dicts hydrated into Jinja + Vue.
- **Payment:** Stripe Checkout/Billing-Portal subscription flow; a webhook mutates `UserPayment` (tier, active state, expiry). Unpaid users see contact-stripped catalog entries.

### Architectural shape

A classic **server-rendered Flask monolith** with a thin client-side enhancement layer. The app is built by a single `create_app` factory wiring **10 blueprints**, SQLAlchemy 2.0 ORM models that also own their own search-indexing and ETL logic, a Typesense derived index, and a **no-build-step Vue 3 (CDN) + TailwindCSS** frontend. External services (Google Cloud Storage, Pub/Sub email bus, Stripe, Sentry, PostHog, Google Maps) are accessed through thin wrapper modules. Production runs on **granian** on **Google Cloud Run**, built by `Dockerfile` + `cloudbuild.yaml`.

The defining characteristics — and the source of most technical debt — are: **fat models** that mix ORM, search, geocoding, and ETL; **fat routes** that mix HTTP, business logic, and serialization; **no automated tests or CI**; **no JS build pipeline**; and **eventually-consistent dual-store sync** maintained by hand-placed `upsert_data()`/`delete_data()` calls.

---

## 2. Architecture at a Glance

### Request lifecycle (production)

```
Internet (HTTPS, TLS terminated by Cloud Run)
        │
        ▼
   granian  (--interface wsgi, --workers 5)   project:application
        │
        ▼
   ProxyFix (x_for/proto/host/prefix = 1)     [prod branch only]
        │
        ▼
   Flask app  (create_app factory)
        │   before_request: assign_anonymous_id
        ▼
   Blueprint route (auth/main/claim/search/profile/settings/
                    payment/admin/onboarding/investment)
        │   guards: @login_required @check_user_info_complete @check_verification [@admin_only]
        ▼
   Model classmethods (get_by_*, get_search, upsert_data, …)
        │
        ├──────────────► Postgres   (source of truth)
        │
        ├──────────────► Typesense  (derived search index)
        │
        └──────────────► External: GCS, Pub/Sub email, Stripe, Maps, PostHog, Sentry
        │
        ▼
   Jinja2 render  →  HTML shell + in-DOM <template> components
        │
        ▼
   Browser: Vue 3 (CDN) mounts #app, fetch() JSON endpoints w/ X-CSRFToken
```

### Layer stack

```
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND      Jinja2 templates + Vue 3 (CDN, no build)      │
│                Tailwind (PostCSS → committed main.css)        │
├─────────────────────────────────────────────────────────────┤
│  ROUTES        10 blueprints (auth, main, search, profile,   │
│                settings, payment, admin, onboarding,          │
│                investment, claim) + bespoke guard decorators  │
├─────────────────────────────────────────────────────────────┤
│  SCHEMAS       Pydantic v2 DTOs — RESPONSE serialization only │
├─────────────────────────────────────────────────────────────┤
│  MODELS        SQLAlchemy 2.0 (also own Typesense sync +      │
│                geocoding + CSV/JSONL ETL — "fat models")      │
├─────────────────────────────────────────────────────────────┤
│  INTEGRATIONS  GCS · Pub/Sub email bus · Stripe · Sentry ·    │
│                PostHog · Google Maps/geopy · feedparser       │
├─────────────────────────────────────────────────────────────┤
│  BOOTSTRAP     create_app factory · extensions · config ·     │
│                flask setup CLI · Dockerfile/cloudbuild        │
└─────────────────────────────────────────────────────────────┘
```

### Dual store (Postgres ⇄ Typesense)

```
        WRITES                                    READS
   ┌──────────────┐                          ┌──────────────┐
   │  Route/CLI   │                          │ Search routes│
   └──────┬───────┘                          └──────┬───────┘
          │ db.session.commit()                     │ Model.get_search()
          ▼                                          ▼
   ┌──────────────┐   upsert_data()/delete_data()  ┌──────────────┐
   │   POSTGRES   │ ─────────────────────────────► │  TYPESENSE   │
   │ (truth)      │   (hand-placed, post-commit,   │ (derived)    │
   │              │    no txn, no retry)           │ embeddings:  │
   │ search_index │ ◄── doc id mirrored back ───── │ MiniLM L12   │
   └──────────────┘                                └──────────────┘
   Drift occurs when: a Typesense write fails after commit, a route
   forgets to call upsert/delete, or a field is cleared (falsy values
   skipped). Only full reindex path is the DESTRUCTIVE `flask setup`.
```

---

## 3. Domain Model

Globalify's schema splits into a **platform-user cluster** and a **catalog cluster**, joined by `Investment` (the funding "check") and by the claim flow (`Investor.user_id`).

**Platform side.** A `User` (OAuth-only identity, Flask-Login root) has one `UserInfo` (profile, `is_complete` gate), one `UserPayment` (Stripe subscription), and many `Notification`/`EmailVerification` rows. Users join `Company`s through `UserCompany` (a membership join carrying a `CompanyRole`), and companies can issue `CompanyInvitation`s. A `Company` owns `FundingRound`s; each round contains `Investment`s.

**Catalog side.** `Investor` and `InvestmentFirm` are large, near-parallel searchable entities (~30 columns, industries/rounds/notable-investments M2M). `Investor` is duplicated three times via the `InvestorBase` abstract mixin: the live `Investor`, plus snapshot tables `InvestorBackup` (single-row, overwritten on each edit, used by "undo") and `InvestorOriginPoint` (created once on claim, used by "restore") — nine parallel association tables in total.

**The bridge.** `Investment.investor_id` / `investment_firm_id` link a company's `FundingRound` to a catalog entity. `Investor.user_id` optionally links a catalog investor to a platform `User` (set by the claim flow). `ClaimRequest` (manual review, `RequestStatus` enum) and `ClaimVerification` (email token) drive that linking. Bookmarks (`CompanyBookmark`, `InvestorBookmark`, `InvestmentFirmBookmark`) and `SearchHistory` are cross-cutting per-user tables. Reference lookups `Industry`/`Round`/`Country` auto-seed via `after_create` DDL listeners.

### ER sketch (compact)

```
User ──1:1── UserInfo
 │  ──1:1── UserPayment (Stripe: customer_id, subscription_id, tier, is_active)
 │  ──1:N── Notification / EmailVerification
 │  ──M:N── Company   (via UserCompany {role, is_primary})
 │  ──1:N── CompanyInvitation / SearchHistory / *Bookmark
 │  ──0:1── Investor   (Investor.user_id, set by claim)
 │
Company ──1:N── FundingRound ──1:N── Investment
                                        │
                       ┌────────────────┴────────────────┐
                       ▼                                  ▼
                  Investor ◄── claim ── ClaimRequest / ClaimVerification
                   │                                  (User claims Investor)
                   ├── InvestorBackup       (undo snapshot, 1 row)
                   ├── InvestorOriginPoint   (restore snapshot, on claim)
                   └──M:N── Industry / Round / NotableInvestment

               InvestmentFirm ──M:N── Industry / Round / NotableInvestment
                   │
                   └──1:N── Investment (investment_firm_id)

   Reference (auto-seeded): Industry · Round · Country
   Search-indexed entities carry a `search_index` column = Typesense doc id
```

---

## 4. Subsystem Tour

### 4.1 Application Bootstrap, Config & Deployment
**What:** `create_app(database_url=...)` (`src/project/__init__.py`) is the single entry point — it calls `sentry_sdk.init` at import (before the Flask object exists), sets all config imperatively on `app.config`, registers 10 blueprints, 6 error handlers, 3 OAuth providers, extensions, the `assign_anonymous_id` before_request hook, and the destructive `flask setup` CLI. `application = create_app()` at module level is the WSGI target granian serves. **Key files:** `__init__.py`, `extensions.py`, `Dockerfile`, `cloudbuild.yaml`, `start.sh/.ps1`, `pyproject.toml`. **MUST know:** (1) There is a **hardcoded fallback `SECRET_KEY`** (a real UUID literal) used when the env var is unset — and `cloudbuild.yaml` does **not** list `SECRET_KEY`, so prod may be running on a forgeable key. (2) **granian is `pip install`ed ad-hoc in the Dockerfile** and is absent from `pyproject.toml`/`uv.lock` — unpinned, unreproducible. Environment selection is imperative (`FLASK_ENV=='testing'` string check + Flask's `DEBUG`), not a config-class hierarchy.

### 4.2 Data Models & ORM Layer
**What:** SQLAlchemy 2.0 typed (`Mapped[...]`, `MappedAsDataclass`) ORM that also owns Typesense indexing, geocoding, and CSV/JSONL ETL — the de-facto data-access + ETL layer. **Key files:** `models/investor.py` (**2009-line god-file**), `models/user.py`, `models/investment.py`, `models/claim.py`, `models/helpers.py`. **MUST know:** (1) Because models are **dataclasses, column declaration ORDER is the constructor signature** — relationships are declared first with `init=False` so they don't become required ctor args; `kw_only`/`insert_default` are load-bearing. (2) Models reach out to the network: **geocoding runs synchronously inside attribute setters and `@validates` hooks**, and `sync_search_index` writes the Typesense id back via a raw **f-string `UPDATE ... CASE id WHEN` SQL** statement. Suggestion engines load entire tables into memory and score every row (O(n) per request).

### 4.3 Authentication, OAuth & Access Control
**What:** Password-less identity via Authlib (Google OIDC, LinkedIn, Apple), Flask-Login sessions/remember-cookie, a separate email-verification OTP flow, anonymous-visitor tracking, and bespoke guard decorators (`check_user_info_complete`, `check_verification`, `admin_only`, investor-mode). **Key files:** `routes/auth.py`, `utils/decorators.py`, `__init__.py` (OAuth registration + Apple JWT). **MUST know:** (1) **LinkedIn is almost certainly broken** — it uses deprecated v1 scopes (`r_liteprofile`/`r_emailaddress`) and raw v2 REST calls, with a hardcoded secret workaround and a typo'd endpoint (`'auth_login'`) that 500s. (2) **Apple's client secret is an ES256 JWT minted ONCE at import** with a 180-day expiry and hardcoded `kid`/`iss`; it returns `None` on failure (silent break). Cross-provider login with the same email is rejected (`OAUTH_MISMATCHED_PROVIDER`). Guard-decorator stacking order is inconsistent across the codebase.

### 4.4 Core Routes (public site, profiles, settings)
**What:** Three blueprints — `main` (marketing/static/vanity pages, dynamic profile getters, bookmarks/notifications, sitemap/robots/health, error handlers), `profile` (greedy `/<username>` catch-all + investor/company mode switching), and `settings` (**1381-line** account/company/membership/investor management). **Key files:** `routes/main.py` (889 lines), `routes/profile.py`, `routes/settings.py`, `utils/parse_medium.py`. **MUST know:** (1) **Flash messages are encoded into URL query params** (`Status(...).get_status()` → `?type=&msg=`), not Flask `flash()` — pervasive across all routes. (2) Several **GET endpoints mutate state** (`update_notification`, mode-switching) bypassing CSRF, and `set_primary = current_user.id` assignments in `profile.py`/`settings.py` lack a following `commit()`, so the primary-company change likely no-ops. The homepage does a live, **TLS-verification-disabled** `requests.get` to the Medium blog on every render.

### 4.5 Domain Routes (investment, claim, onboarding, payment)
**What:** Four business-workflow blueprints. `investment.py` is CRUD over `FundingRound`/`Investment`; `claim.py` runs the two claim paths; `onboarding.py` gates access via `UserInfo.is_complete`; `payment.py` is the Stripe lifecycle + webhook. **Key files:** `routes/investment.py`, `routes/claim.py`, `routes/onboarding.py`, `routes/payment.py`. **MUST know:** (1) **`investment.py` has NO authorization beyond `is_verified`** — any verified user can create/edit/delete any investment or funding round for any company (likely meant to be admin-only). (2) The **Stripe webhook is fail-closed but fragile**: when `_STRIPE_WEBHOOK_SECRET` is set it verifies the signature correctly; when unset, `event` is never assigned so the handler returns `"Event not found"` before processing — i.e. *all* webhooks (including legitimate ones) silently no-op, so a misconfigured deploy means payments never update entitlements. The `else` branch that reads unsigned `data`/`event_type` is dead code. *(Note: an earlier pass flagged this as a spoofing hole; on verification it is NOT exploitable — it bails before the `match`.)* There is also a `Tier` enum value mismatch (`'premium monthly'` vs Stripe's `premium_monthly`) that silently mis-tiers users, and webhook handler errors are swallowed (always returns 200, so Stripe never retries).

### 4.6 Admin Routes
**What:** Operator console: per-entity CRUD, moderation/approval queues, Typesense management, duplicate detection/merge, and company/user membership — six child blueprints mounted under `admin`. **Key files:** `routes/admin/__init__.py`, `routes/admin/investor.py` (794 lines), `company.py`, `investment_firm.py`, `user.py`, `investments.py`, `funding_round.py`. **MUST know:** (1) **Near-total copy-paste duplication** across the six modules with no shared abstraction, plus latent bugs: `company.search_notable_investment` is the **only route missing `@admin_only`** (publicly leaks data); `delete_data()` deletes by Postgres id instead of the Typesense `search_index` (**orphaned/zombie search documents**); `merge_investors` creates a merged row but never deletes the sources; duplicate detection only scans the first 1000 rows. (2) Privileged fields (`is_admin`, `is_approved`, payment tier) are **mass-assigned from raw JSON** with no validation, protected only by session auth.

### 4.7 Typesense Search
**What:** Full-text + semantic (vector) search, faceting, sorting, and autocomplete over investors, firms, companies, and cities. A single module-level client, a fluent `SearchBuilder`, and three collections whose schemas live inline inside each model's `sync_search_index`. **Key files:** `utils/typesense_helpers/typesense_search.py`, `routes/search.py`, `models/investor.py` & `user.py` (schemas + `get_search`). **MUST know:** (1) **Country faceting is silently broken** — schemas define field `country` but `Investor`/`InvestmentFirm` `get_search` filter on `countries` (plural), so it never matches (Company is correct). (2) **`get_search` swallows all exceptions and returns empty results**, so a Typesense outage or misconfig looks identical to "no results." Vector search is opt-in (include `embedding` in `query_by`); embeddings are computed server-side by Typesense via `ts/all-MiniLM-L12-v2`. The only full-reindex path is the destructive `flask setup`.

### 4.8 External Integrations
**What:** Thin wrappers for GCS (image upload/processing), **Pub/Sub as the async email bus** (actual sending lives in a separate `globalify-email-service` GCP project — there is **no SendGrid code in this repo** despite the dependency), Stripe, Sentry, PostHog (server + client), Google Maps/geopy geocoding, and feedparser. **Key files:** `utils/google_helpers/google_pubsub.py` & `google_storage.py`, `utils/posthog.py`, `utils/suggestion.py`, `routes/payment.py`. **MUST know:** (1) **`send_event` blocks the request thread** on `futures.wait(ALL_COMPLETED)` with no timeout — a slow Pub/Sub stalls signup/onboarding/invites; the global `publish_futures` list also grows unbounded. (2) **Clients are constructed at import time** (`PublisherClient`, `googlemaps.Client`, `stripe.api_key`), so a missing/invalid credential crashes the whole app on boot rather than degrading gracefully. The client-side PostHog key is hardcoded and copy-pasted across ~6 templates.

### 4.9 Utilities, Scrapers & Data Population
**What:** Data ingestion (CSV/JSONL bulk loads), Medium RSS scraping, faker demo data, pagination/formatting helpers, enums/error strings, and a 1642-line static reference dataset (`info_lists.py`). **Key files:** `utils/scraper.py` (misnamed — **no live scraper**), `utils/scraper_helpers/population.py`, the `populate_*` staticmethods inside `models/investor.py`, `utils/parse_medium.py`, `data/`. **MUST know:** (1) **"Scraping" means parsing pre-downloaded flat files** committed under `data/` (the only live fetch is the Medium RSS). Population logic is **triplicated** (`scraper.py`, `population.py`, inline in `investor.py`) and has silently diverged; most utils copies are dead relative to the live `flask setup` path. (2) Token reconciliation uses **`thefuzz` ratio with magic thresholds (80/90/99)** and **silently drops unmatched tokens** — ingestion is lossy and non-deterministic.

### 4.10 Pydantic Schemas / Validation Layer
**What:** Pydantic v2 DTOs used **almost exclusively for response serialization** (ORM → JSON for Vue) — **not** for request validation, not for Typesense shaping. **Key files:** `schemas/investor.py`, `schemas/user.py`, `schemas/investment.py`, `schemas/profile.py`, `schemas/notification.py`. **MUST know:** (1) **There is zero structured input validation** — all inbound payloads are parsed ad-hoc in routes. (2) The dominant pattern is **manual field-by-field construction** (`Schema(id=obj.id, name=obj.name, …)`) repeated across ~20 sites; only `search.py` uses idiomatic `model_validate(orm, from_attributes=True)`. There are **two colliding `InvestorSchema` classes** (full vs minimal), `object`/`list[object]` passthrough fields that defeat validation, and `model_dump()` overrides that hand-format dates/enums instead of using `mode='json'`.

### 4.11 Frontend Templates (Jinja2 + Vue 3 CDN + Tailwind)
**What:** Server-rendered Jinja that mixes three rendering models: pure static pages, Jinja shells that bootstrap CDN Vue from in-DOM `<template>` components, and hidden-input hydration. **Key files:** `templates/layouts/*.html`, `templates/components/navbar.html` (composition root), `full_investor.html`, `search.html`. **MUST know:** (1) **~11 "app" pages do NOT extend any layout** — each is a complete document copying the full `<head>`, PostHog snippet, Vue CDN, and navbar/aside inline, so a meta change requires editing dozens of files. (2) **Vue uses custom delimiters `[[ ]]`** so Jinja `{{ }}` is server-evaluated *inside* Vue templates (e.g. `v-if="... == {{ user.id if user else 0 }}"`) — two engines render the same file in two passes, tightly coupled. Several dead files exist (`layout_payment.html`, `gemini.html`).

### 4.12 Frontend JS (Vue 3 CDN) & Styling (Tailwind)
**What:** No-build client layer. Each page loads Vue from CDN, then `base.js` (shared components), then a page script. Options API only, in-DOM templates, imperative DOM manipulation. Tailwind compiled offline into a committed `main.css`. **Key files:** `static/vue/base.js`, `main.js`, `settings.js` (~1795 lines), `admin.js` (~1811 lines), `investorOnboarding.js`, `tailwind.config.js`. **MUST know:** (1) **Script load order is load-bearing and undocumented** — page scripts depend on `base.js` having created globals first; there's no module system. (2) **Tailwind's content glob scans only templates, not the Vue JS files**, so classes hardcoded in JS can be purged and silently break styling. Massive duplication (wizard + investment/funding-round components copy-pasted across settings/admin/onboarding), the fetch+CSRF block repeated ~80×, and **offensive debug strings shipped to prod** (`'YA GEI'`, `'im gay'` in `settings.js`).

---

## 5. Cross-Cutting Concerns & Conventions

- **Env-var underscore convention.** App-specific secrets are prefixed with a leading underscore (`_DATABASE_URL`, `_GOOGLE_OAUTH2_*`, `_TYPESENSE_*`, `_STRIPE_*`, `_PUBSUB_*`, ~30 total) to distinguish them from framework vars (`SECRET_KEY`, `FLASK_ENV`, `FLASK_DEBUG`, `PORT`). Mirrored in `cloudbuild.yaml` substitutions. Locally loaded by `start.sh`/`start.ps1`.
- **Query-param flash.** `Status(StatusType, msg).get_status()` returns a dict spread into `url_for(..., **status)`, producing `?type=&msg=` read back by the next page. Used everywhere instead of Flask `flash()`. `StatusType` values are string-compared as `'1'/'2'/'3'` in templates.
- **CSRF + JSON fetch.** Flask-WTF `CSRFProtect` is real but disabled when `WTF_CSRF_ENABLED=False` (testing/some debug). Vue reads a hidden `<input id="csrf_token">` via `getElementById` and sends `X-CSRFToken` on every write — copy-pasted ~80× in JS and ~54× in templates.
- **No-build CDN Vue.** Vue 3 loads from jsDelivr per page; components are Jinja macros wrapping in-DOM `<template id>` registered via `defineComponent({template:'#id'})`. Custom `[[ ]]` delimiters let Jinja and Vue coexist. No bundler, router, or store.
- **Dual-store sync.** Postgres is truth; Typesense is derived. Kept eventually-consistent by hand-placed `upsert_data()`/`delete_data()` calls co-located with mutating routes — no transaction wrapping, retry, or reconciliation. The Typesense doc id is mirrored back into each row's `search_index` column.
- **Fat models / thin-ish routes.** Data access lives on models as `@staticmethod`/`@classmethod` repository wrappers (`get_by_id`, `get_search`, `upsert_data`); routes orchestrate and serialize. But business logic (SEO strings, paywall, backup mirroring) leaks into routes too.
- **The `flask setup` seed flow.** The real bootstrap entry point: `db.drop_all()` + `create_all()` → seed 2 hardcoded admins → `Investor.populate_demo()` (data/investor.csv) + `InvestmentFirm.populate_vcsheet()` → slugify → `sync_search_index(recreate=True)`. **Destructive and non-idempotent** — it is also the only full-reindex path. Reference data (Industry/Country/Round) auto-seeds via `after_create` DDL event listeners.
- **Email is fully decoupled** via Pub/Sub to an external `globalify-email-service` GCP project — `sendgrid` in `pyproject.toml` is a dead dependency in *this* repo.

---

## 6. Health Assessment & Risks

Synthesized into themes, ranked by severity.

### CRITICAL — security holes that must be closed before any public revival
1. **Forgeable sessions.** Hardcoded fallback `SECRET_KEY` in source; `cloudbuild.yaml` doesn't set it → prod may run on the literal key, enabling session + remember-me cookie forgery. (`__init__.py:76`)
2. **Open CRUD on financial data.** `investment.py`'s 8 endpoints have no `@admin_only` or ownership check → any verified user mutates any company's investments/rounds by id (IDOR). ✅ verified.
3. **Mass-assignment of privileged fields.** Admin JSON endpoints (and `create_investment`'s `created_by_admin`) set privileged flags like `is_admin`/`is_approved`/tier from raw input with no validation (session-auth only, no CSRF on JSON POSTs).

> *Reclassified from CRITICAL to HIGH after verification:* **Stripe webhook fragility.** When `_STRIPE_WEBHOOK_SECRET` is unset the handler returns `"Event not found"` before processing (fail-closed, NOT spoofable) — but this means a misconfigured deploy makes *all* billing webhooks silently no-op. Verified at `payment.py:419-445`. Fix for clarity + reliability, not as a security hole.

### HIGH — correctness & reliability
5. **Search drift & broken filters.** Hand-placed, non-transactional Typesense sync drifts permanently on any failure; `delete_data()` deletes the wrong key (zombie docs); **country faceting silently broken**; `get_search` masks outages as empty results; only reindex path wipes the DB.
6. **Broken/expiring auth providers.** LinkedIn uses retired v1 scopes/endpoints (likely dead); Apple secret minted once with 180-day expiry, fails to `None` silently.
7. **Blocking external calls in the request path.** `send_event` blocks on Pub/Sub with no timeout; homepage does a live TLS-disabled blog fetch with no cache/timeout; import-time client construction crashes the whole app on bad creds.
8. **Silent state desync.** Webhook handler errors swallowed (always 200, no Stripe retry); `Tier` enum value mismatch mis-tiers users; `is_complete` set in 3 places; `expire_all_by_user_id` writes a read-only `@property` so verification codes are **never invalidated**.

### MEDIUM — maintainability & structure
9. **Oversized, multi-concern modules.** `investor.py` (2009 lines), `settings.py` (1381), `admin.py`/`settings.js` (~1800 each), `info_lists.py` (1642). God-files block comprehension and safe change.
10. **Model ↔ route ↔ search coupling.** Models own ETL/geocoding/Typesense; routes own business logic/serialization. Single-responsibility violated throughout.
11. **Pervasive duplication.** Triplicated population logic; copy-pasted admin CRUD; ~80× fetch/CSRF blocks; duplicated server-page vs Vue-modal entity views; three duplicated embedding schemas.
12. **Lossy/non-deterministic ETL.** Fuzzy-ratio matching with magic thresholds silently drops tokens; `ast.literal_eval` on CSV cells aborts whole imports on one bad row.

### MEDIUM/LOW — process & supply chain
13. **No tests, no CI.** `.github` has only `dependabot.yml` (pip only). Tests/ruff/pre-commit exist but nothing enforces them; Cloud Build deploys on commit with `--no-cache` and no gate.
14. **No JS build pipeline.** CDN Vue with no SRI/version-pinning (some pages load unpinned `@3`), Tailwind output committed to git (drift risk), no lint/typecheck → typos and dead code ship.
15. **Dormancy drift.** ~14 months stale: Stripe API version, PostHog/Google SDK signatures, Vue/Tailwind, and base Docker image are all likely out of date.
16. **Embarrassing artifacts in prod.** Offensive debug strings (`'YA GEI'`, `'im gay'`), `print(e)` everywhere, `position="sex"` placeholder, hardcoded vanity bio routes.

---

## 7. Prioritized Modernization Roadmap

Tailored to *reviving a dormant app*: stop the bleeding first (security + boot reliability), then make it maintainable, then modernize the stack.

### Phase 0 — Quick wins (do first; days, not weeks)
| Item | Rationale | Effort |
|---|---|---|
| Remove hardcoded `SECRET_KEY` fallback; **fail fast** if unset (non-debug); set it in `cloudbuild`/Secret Manager | Closes critical cookie-forgery hole | S |
| Fix Stripe webhook control flow: require `_STRIPE_WEBHOOK_SECRET` (fail loudly at boot), delete the dead unsigned `else` branch, return non-200 on handler errors so Stripe retries | Webhooks currently no-op silently without the secret; reliability not spoofing | S |
| Add `@admin_only`/ownership to `investment.py` and the un-gated `company.search_notable_investment` + unauthenticated onboarding helpers | Closes open-CRUD + info-leak | S |
| Pin & add **granian to `pyproject.toml`**; remove ad-hoc `uv pip install` | Reproducible prod server | S |
| Fix the **`countries`→`country`** filter bug; fix `delete_data` to delete by `search_index`; fix `expire_all_by_user_id` to set `is_used` | Restores faceting, search deletes, code invalidation | S |
| Remove offensive debug strings, `print`-debugging, `position="sex"`, dead files (`layout_payment.html`, `gemini.html`) | Professionalism + clarity | S |
| Make `send_event` **non-blocking** (drop `futures.wait`, add timeout) | Removes request-path stall | S |
| Cache Medium feed + re-enable TLS verification + timeout | Homepage can't be taken down by the blog | S |
| Add **GitHub Actions CI** (ruff lint/format + pytest + `uv sync`); gate Cloud Build on it | Enforces existing-but-unrun quality tooling | S |
| Add a **standalone reindex CLI** decoupled from `db.drop_all` | Safe prod reindex | S |

### Phase 1 — Foundational (weeks; make it safe to change)
| Item | Rationale | Effort |
|---|---|---|
| **Typed settings layer** (pydantic-settings) for all env vars; fail fast on missing secrets; move kid/iss/team-id/bucket/topic out of code | Eliminates silent-None secrets, hardcoded defaults, scattered `os.getenv` | M |
| **Lazy client factories** with retries/timeouts + Sentry capture (GCS, Pub/Sub, Maps, Stripe) | App boots in degraded mode instead of import-crash | M |
| **Request-validation Pydantic schemas + a validation decorator** across mutating endpoints; adopt `model_validate(from_attributes=True)` everywhere for responses | Closes the zero-input-validation gap; kills ~20 hand-mapped DTO sites and date-parse 500s | L |
| **Auth hardening:** LinkedIn → OIDC; Apple secret as per-request callable; `login_view` + `session_protection='strong'` + secure cookie flags; one canonical guard order; validate `next` | Fixes broken/expiring providers and session hardening | M |
| **Stripe webhook refactor:** mandatory signature, idempotency by event id, single lookup_key→Tier map, propagate failures for retries | Fixes spoof + mis-tier + silent desync in one pass | M |
| **Move Typesense sync to SQLAlchemy `after_commit` listeners (or outbox + worker)** + nightly reconcile | Eliminates the entire drift class; removes blocking calls from requests | M→L |
| **Extract Typesense indexing + geocoding + ETL out of models** into services; split `investor.py`/`settings.py`/`admin.py` god-files | Restores single responsibility; makes models testable | L |
| **Generic admin CRUD base** (MethodViews/registration DSL) | Removes ~80% of copy-pasted admin code and its latent bugs | L |
| **Idempotent seed + Alembic-based bootstrap** (no `drop_all` in normal flows); move bulk data out of git | Safe revival/onboarding; reproducible seeding | M |
| **Add DB indexes/constraints** on FKs and hot query paths; standardize ondelete/cascade and tz-aware datetimes | Query performance + integrity on revival | M |
| **Auth + webhook + claim test suite** | These subsystems have multiple silent-failure branches tests would catch | L |

### Phase 2 — Ambitious (modernize the stack)
| Item | Rationale | Effort |
|---|---|---|
| **Frontend build (Vite) + migrate in-DOM templates to Vue SFCs**, self-host/pin Vue, add SRI | Removes load-order fragility, the `[[ ]]` hack, dual-render coupling; enables HMR/tree-shaking/typecheck | XL |
| **Shared API fetch helper + shared component library** (dedupe wizard/investment components, ~80 fetch blocks) | Halves `settings.js`/`admin.js`; one place for CSRF/error handling | L |
| **Single shared base layout** for app pages + extract PostHog/footer/meta/SVG partials | One-edit global changes; fix duplicate `csrf_token` IDs | M |
| **Push suggestion ranking into Typesense** (embeddings already exist); replace in-memory O(n) scoring | Won't scale past a few thousand rows otherwise | M |
| **Replace cloned `InvestorBackup`/`InvestorOriginPoint` tables** with JSONB snapshot or temporal versioning | Removes triple schema maintenance + 9 association tables | L |
| **Move secrets to GCP Secret Manager**; pin Docker base by digest; broaden dependabot (npm/docker/actions) | Supply-chain best practice for ~30 secrets incl. private keys | M |
| **Upgrade & re-verify all SDKs** (Stripe API version, PostHog, google-cloud-*, sentry, Vue, Tailwind v4); remove dead `sendgrid` | Closes 14-month dormancy drift | L |
| **ESLint + Prettier + Vitest** for the frontend | Catches the typo'd state keys, broken `deleteResponses.ok`, dead Cyrillic methods | M |
| **Consolidate population into one tested ingestion package** with per-row error handling + coverage report; replace fuzzy matching with embedding/ID mapping | Observable, reproducible, non-lossy imports | M |
| Accessibility pass + replace full-page-reload search with history-driven partial updates | UX quality on the core flow | M→L |

---

## 8. Open Questions (deduped, ordered by importance to revival)

1. **Is `SECRET_KEY` actually set in production?** `cloudbuild.yaml` omits it — prod may be on the hardcoded default (cookie forgery). *Resolve before any public exposure.*
2. **Is `_STRIPE_WEBHOOK_SECRET` set in prod?** If not, the webhook handler returns "Event not found" and *all* billing events silently no-op (entitlements never update). Not a spoofing risk, but a billing-correctness one.
3. **Does anything run `flask db upgrade` on deploy?** Dockerfile/cloudbuild only start granian; the migration-application path is unclear, and `flask setup` is destructive.
4. **Are `investment.py` CRUD endpoints meant to be admin-only?** Determines whether the missing auth is a critical bug or these are only reachable from an admin UI.
5. **Is LinkedIn / Apple login currently functional?** LinkedIn uses retired scopes; Apple's secret expires 180 days after each process start. Both may have been silently broken for months.
6. **Where is the external `globalify-email-service` (Pub/Sub subscriber)?** It owns the actual email sending (SendGrid + templates) and the claim-token delivery — needed for a full email revival.
7. **Is there any non-destructive production reindex mechanism?** Or is the index only ever maintained via per-record upserts plus the DB-wiping `flask setup`?
8. **Which seeders/data files are live vs orphaned?** Only `populate_demo` + `InvestmentFirm.populate_vcsheet` run; `populate_all/populate/populate_cli/populate_blockchain` and several `data/*.jsonl` (e.g. `cities_index.jsonl` 7.4M) appear unreferenced.
9. **Is the dual `InvestorBackup` (undo) vs `InvestorOriginPoint` (restore) design intentional**, and which is the source of truth after a claim+edit? Is the snapshot ever consumed by a UI, or is it write-only?
10. **Is the in-house `SuggestionBuilder` still used at request time**, or superseded by Typesense embeddings? Both exist; one may be dead.
11. **Are `InvestmentFirm` and `Investor` still distinct product-wise?** Near-identical schemas + Investment FKs suggest a possible merge.
12. **Under what config is `WTF_CSRF_ENABLED=False`** — testing only, or any deployed env? Determines real CSRF exposure of the JSON endpoints.
13. **Stripe API version pinning** — do webhook payload shapes (`current_period_end`, line-item `subscription`) still match after a likely-old default version?
14. **Are the `construction()` / footer routes** (`/investor-database`, `/startup-database`, `/digest`, `/docs`, `/jobs`, `/partners`) intended revival features or dead links to delete? And are the vanity bio pages (`eric`/`jennifer`/`arstan`) still wanted?
15. **Is the Twitter/X timeline embed expected to work** given X deprecated the public widgets API? Several profile UIs depend on it.