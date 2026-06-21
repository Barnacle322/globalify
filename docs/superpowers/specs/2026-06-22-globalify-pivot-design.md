# Globalify Pivot — Master Design (North Star)

**Date:** 2026-06-22
**Status:** Design approved in brainstorming; per-phase specs to follow.
**Companion docs:** [`docs/codebase-map.md`](../../codebase-map.md) (current-state audit), [`docs/pivot-research.md`](../../pivot-research.md) (sourced research brief).

This is the north-star design for repositioning Globalify from a dormant, failed-monetization investor *platform* into an open, SEO-first investor *database*. It defines the vision, architecture, data model, monetization, and a phased roadmap. Each phase gets its own focused spec → implementation plan.

---

## 1. Vision & positioning

**Globalify becomes an open, SEO-first directory of investors and VC firms.** The bet: maximize indexable surface and organic traffic, keep the core data free and open, and monetize lightly via ads + a cheap Pro tier. The dead platform side (company profiles, team management, user-entered deals, paywalled discovery) is removed.

- **Primary content (hero):** investors (people) and investment organizations (firms/funds). These are the pages that rank and drive traffic.
- **Secondary content:** startups remain as *thin* supporting pages (enrich "who funded whom", capture long-tail queries). Not a hero entity.
- **Audience:** founders searching for investors ("seed fintech investors in Berlin", "angels who back climate", a specific firm/partner by name), plus general research traffic.
- **Principle:** open by default. The content is free, crawlable, and never gated. Money comes from ads on free pages and from Pro *tools/conveniences*, never from locking the core information.

### Core user journeys
- **Anonymous visitor (the 95%):** lands from Google on a profile or facet page → browses freely → ad-supported. No login wall, ever.
- **Pro subscriber:** pays ~$7/mo (or one-time lifetime) → no ads, advanced/combined filters, saved searches, email alerts, CSV export, full contact info.
- **Claimer (investor/firm):** authenticates by email magic-link → claims and enriches their own profile → verified badge. A free growth + freshness + SEO loop that brings the subjects to the site.

---

## 2. Architecture

A server-rendered **Flask monolith**, deliberately simple. Existing strong foundations (Postgres, Typesense) are kept; the SPA, OAuth, and dead integrations are removed.

```
Internet (Cloud Run, TLS)
   → granian (WSGI)  →  Flask app (create_app)
      → Jinja SSR pages (public, crawlable, JSON-LD)  ←─ primary surface
      → small htmx/Alpine sprinkles (filters, bookmark button)
      → Postgres (source of truth)  ⇄  Typesense v30 (single search collection)
      → Resend (email)   R2 (images)   Paddle (billing)   Cap (captcha)
      → scheduled data collectors (public-domain sources → entity resolution → Postgres → Typesense)
```

### Stack changes (from → to)

| Area | From | To |
|---|---|---|
| Runtime | Python 3.12 | **Python 3.14** |
| Frontend | Vue 3 (CDN SPA, no build) | **Flask + Jinja SSR** + htmx/Alpine sprinkles |
| Auth | Google/LinkedIn/Apple OAuth | **Magic-link email** (passwordless) |
| Payments | Stripe | **Paddle** (Merchant of Record) |
| Email | SendGrid via Pub/Sub | **Resend** (direct) |
| Storage | Google Cloud Storage | **Cloudflare R2** (S3-compatible) |
| CAPTCHA | Google reCAPTCHA v2 | **Cap** (trycap.dev, self-hosted) |
| Async bus | Google Pub/Sub | **deleted** |
| Search | Typesense v26 / client 0.21 | **Typesense v30.2 / client 2.0** |
| Embeddings | built-in MiniLM | **Gemini** (`gemini-embedding`, remote) |
| Dependencies | stale (2023–24) | **all bumped to current majors** |

### Dependency overhaul
- **Bump:** Flask, Flask-SQLAlchemy/SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Pillow, pydantic, Sentry, etc. to current majors. Verify 3.14 wheels exist for each; fall back to 3.13 only if a critical dep lags.
- **Remove (dead/replaced):** `stripe`, `sendgrid`, `google-cloud-storage`, `google-cloud-pubsub`, `authlib`, `googlemaps`, `flask-debugtoolbar` (optional), `pillow-heif` (keep if HEIC uploads still needed).
- **Add:** `typesense>=2.0`, `paddle-python-sdk`, `resend`, `boto3` (R2). Keep `flask-login`, `geopy` (geocoding via Nominatim if needed), `python-slugify`, `thefuzz`/entity-resolution libs.

---

## 3. Data model

**Decision: consolidate.** Replace the twin `Investor` (person, with denormalized `firm_name` string) and `InvestmentFirm` (org) tables — and their ~9 duplicated association tables — with a **Person + Organization + Affiliation** model. This mirrors how Crunchbase/PitchBook/NFX Signal model investor data (people and orgs as distinct entities joined by a time-bounded role edge) and removes the largest source of duplication in the codebase.

### Core tables
- **`person`** — `id, slug (UNIQUE), first/last/full_name, headline, about, person_type (enum, nullable), socials/contact, location, geography_id, user_id FK (nullable, set by claim), is_public, is_approved, search_index, timestamps`.
- **`organization`** — `id, slug (UNIQUE), name, org_type (enum), is_investor (bool), about, website/linkedin/twitter/email, hq geography_id, founded_year, n_employees, aum_usd, is_public, is_approved, search_index, timestamps`.
- **`affiliation`** (replaces `firm_name`) — `person_id FK, organization_id FK, title, role (enum), is_current, is_lead, started_on/ended_on, UNIQUE(person_id, organization_id, title)`. Supports partners moving firms, multiple partners per firm, and a person who is both an angel and a partner.
- **`investor_profile`** (polymorphic: a person OR an org can carry investment criteria) — `subject_type ('person'|'organization'), subject_id, investor_type (enum), check_size_min_usd, check_size_max_usd, sweet_spot_usd, lead_preference (enum), thesis_summary, accepts_cold_inbound (bool), application_url, fund_size_usd, vintage_year, num_investments, num_lead_investments, num_exits, last_investment_date, is_active, data_source, verified, verified_at, claimed_by_investor, UNIQUE(subject_type, subject_id)`.
- **Shared polymorphic facet joins** (replace the 9 duplicated M2M tables with 4): `entity_industry`, `entity_stage`, `entity_geography`, `entity_notable_investment`, each keyed `(subject_type, subject_id, <facet>_id)`.
- **`geography`** — `id, name, slug, type (country|region|city), country_code, lat/lng`. Replaces free-text location strings; gives stable slugs for `/investors/london`-style geo pages.
- **`investment`** — repointed from separate `investor_id`/`investment_firm_id` columns to a single `(investor_subject_type, investor_subject_id)`.
- **`fund`** — reserved as a distinct type, **deferred** (don't cram funds into `organization`); add when AngelList/PitchBook-style vehicles are needed.

> **Polymorphic vs strict FK:** the polymorphic `(subject_type, subject_id)` joins trade DB-level FK integrity for far fewer tables. Default to polymorphic; revisit per-table if integrity bugs appear (alternative: two nullable FK columns).

### Enums
- **`org_type`:** `vc_firm, micro_vc, angel_group, corporate_vc, family_office, accelerator, incubator, venture_studio, pe_firm, growth_equity, syndicate, lp_fund_of_funds, grant_program, government_program, venture_debt, crowdfunding_platform, search_fund, hedge_fund, other`.
- **`person_type`:** `angel, partner, operator, scout, lp`.
- **`affiliation.role`:** `founder, gp, partner, principal, associate, scout, advisor, lp, operator`.
- **`investor_type`** (canonical classification, the SEO-facet enum): the union of the above capital-source types, mapped to a coarser public bucket set for landing pages.
- **`lead_preference`:** `lead, follow, both, unknown`.

> Exact enum *string* parity with Crunchbase/OpenVC is unverified (their pages 403 to fetchers) — confirm against live UIs before freezing; values above are the working set.

### High-value fields (★ = programmatic-SEO facet)
- **Classification:** `investor_type`★, `org_type`★, `stages[]`★, `sector_focus[]`★, `geo_focus`★ (structured geography).
- **Criteria:** `check_size_min/max_usd` (numeric — derive display bands at query time, do **not** store buckets)★, `lead_preference`★, `thesis_summary`, `fund_size_usd`, `vintage_year`, `aum_usd`.
- **Activity:** `num_investments`, `num_exits`, `last_investment_date` (recency signal), `notable_investments[]`, `co_investors[]`, `is_active`.
- **Contact (high-conversion, Pro-gated for full detail):** `accepts_cold_inbound`★, `application_url`, `contact_channels {email, linkedin, twitter, calendly, form}`, decision-maker `partners[]`.
- **Provenance (E-E-A-T):** `data_source`, `verified`, `verified_at`, `claimed_by_investor`, `updated_at`.

### Typesense projection
Collapse the two collections into **one** (`entities`) with an `entity_type` ('person'|'organization') facet — every facet page becomes one filtered query over one schema and one URL template. Person docs carry `affiliated_firm_name/slug`; org docs carry `partner_names[]`. Adopt:
- **Hybrid search** (keyword + vector) with `rerank_hybrid_matches` for the main search box.
- **Decay functions** in `sort_by` for recency (`last_investment_date`) and geo-distance ranking.
- **Global synonym sets** (v30) for investor vocabulary (VC ↔ venture capital, stage/sector aliases).
- **Gemini embeddings** via Typesense's remote embedder (Google). Entity docs embedded on index/update; free-text queries embedded at search time. Facet-only browsing requires no embeddings.

---

## 4. SEO engine (the priority)

- **Server-rendered Jinja** for all public pages — full HTML, readable with JS disabled. No SPA payload.
- **URL structure:** `/` · `/investors` · `/investors/<slug>` · `/firms` · `/firms/<slug>` · `/startups/<slug>` · programmatic facet pages `/investors/<type|stage|sector|geo>` and cross-products `/investors/seed/fintech`, `/fintech-investors/london`. Filters are GET params; popular combinations promoted to pretty URLs with `rel=canonical` to dedupe.
- **Programmatic facet pages are the #1 traffic lever** — thousands of crawlable pages targeting TYPE×STAGE, TYPE×SECTOR, STAGE×GEO, SECTOR×GEO (mirroring OpenVC's `/investor-lists/<facet>` pattern). Each links into its filtered set and to related entities.
- **Structured data (JSON-LD):** `Person`, `Organization`, `BreadcrumbList`, `ItemList` on browse pages.
- **One shared base layout** (kills today's ~11 pages that each duplicate `<head>`), per-page title/meta/OG, auto-generated segmented **XML sitemaps**, `robots.txt`, canonical tags, strong internal linking, fast Core Web Vitals.

---

## 5. Monetization

- **Free tier:** everything readable + basic search, **ad-supported**. Start with house/sponsor slots (provider-swappable; not AdSense day one). Ads never block content or crawlers.
- **Pro (~$7/mo, or one-time lifetime):** no ads · advanced/combined filters · saved searches · email alerts · CSV export · **full contact info** (free users see it locked — and locked contact is **not** rendered into the page HTML, so it can't leak or be scraped).
- **Billing — Paddle (Merchant of Record):** one Product with two Prices (monthly subscription + one-time lifetime with `billing_cycle: null`). **Webhooks are the source of truth**, not the JS callback: handle `transaction.completed` (lifetime grant via `customData.user_id`), `subscription.created/activated`, `subscription.updated` (catch-all), `subscription.canceled` (revoke at period end). Verify the `Paddle-Signature` HMAC over the **raw** body; dedupe on `event_id`. Paddle auto-handles VAT/sales tax and remittance — no self-managed tax logic, accounting expects net payouts.
- **Stripe:** removed entirely. Zero active subscribers assumed — no migration, no parallel-run.
- **Entitlement:** a simple `is_pro` + `pro_source` (subscription|lifetime) + `pro_expires_at` on the user, flipped by webhooks.

---

## 6. Auth & captcha

- **Magic-link email only** (no OAuth, no passwords). Stateful tokens: `secrets.token_urlsafe(32)`, store `sha256(token) + user_id + purpose + expires_at + consumed_at` in a `login_tokens` table; email a verify link via Resend; on click validate (unexpired + unconsumed) → mark consumed → `login_user`. Stateful chosen for revocation + auditability (claim flow). A `purpose` discriminator reuses the mechanism for login, claim-verification, and alerts.
- **Cap (self-hosted captcha)** on the only unauthenticated write surfaces: the **magic-link send endpoint** (prevents email-bombing) and **claim submission**. Cap exposes a reCAPTCHA-compatible `siteverify`, so the server check is a near-drop-in; deploy Cap Standalone as a Docker container alongside Typesense. Remove all reCAPTCHA (`g-recaptcha` widgets, `claim.py` Google `siteverify`, `_GOOGLE_RECAPTCHA_*` keys).

---

## 7. Email & storage

- **Resend:** `send_email(to, subject, html)` helper; render Jinja `email/*.html` to an HTML string (Resend has no server-side templating). Verify a **sending subdomain** (`mail.globalify.…`) with SPF/DKIM/DMARC; never send from the root domain. Retry on 429 honoring `ratelimit-reset`.
- **Cloudflare R2 (via boto3):** `endpoint_url=https://<ACCOUNT_ID>.r2.cloudflarestorage.com`, `region_name='auto'`. **Free egress** is the decisive win for serving images. Serve via a **Custom Domain** (`img.globalify.…`) — never `r2.dev` in prod. Keep the existing Pillow/pillow-heif processing **verbatim** (it's storage-agnostic); swap only the I/O layer. **Store the UUID key in Postgres, not the full URL**; compute URLs at render time. Browser-direct uploads (logo claims) via presigned PUT. Note R2 has no per-object ACLs/bucket policies/versioning. One-off migration script copies GCS blobs → R2 preserving keys.

---

## 8. Automated data collectors (freshness engine)

Existential for an SEO directory: stale data ranks poorly and erodes trust. **Public-domain sources first**, expand later.

- **Source priority (v1):** **SEC EDGAR** (Form D / Form ADV / 13F — public domain, official JSON API + bulk; requires descriptive User-Agent, ≤10 req/s) as the authoritative US backbone and dedup keys (CIK/CRD); **Crunchbase Open Data Map** (free with attribution — name, description, logo, location, socials) as the seed skeleton; **public company registries** (Companies House, EU BRIS) for entity resolution. Defer paid Crunchbase/Dealroom.
- **Architecture:** per-source collector workers → **raw immutable landing tables** (`source, fetched_at, payload`) → **normalize / entity-resolve** (block on CIK/CRD/domain/normalized-name; probabilistic matching) → **canonical Postgres tables** → **incremental upsert → Typesense**. Separate raw vs canonical for reprocessing + provenance.
- **Cadence:** EDGAR daily + quarterly bulk; registries weekly/monthly; news/RSS hourly for funding-round freshness ("recently active" signal). Scheduled via cron/APScheduler/Celery beat.
- **Legal posture:** public-domain/official datasets and opt-in attribution sources only for v1; honor robots.txt + rate limits; never bypass auth; keep a per-source license register. Broader scraping is explicitly deferred (revisit with counsel, especially for EU personal data).

---

## 9. What gets deleted

Companies + teams + invitations + `UserCompany`; entrepreneur/investor onboarding wizards; user-entered funding rounds/investments; investor-mode switching; vanity/marketing pages (`eric`/`jennifer`/`arstan`, `construction`, `gemini`, etc.); public crowdsourcing; the entire Vue 3 SPA + `static/vue/*`; OAuth (`authlib`, Google/LinkedIn/Apple); Stripe; Google Cloud Storage; Google Pub/Sub + the external `globalify-email-service`; SendGrid; reCAPTCHA. Net effect: a large simplification (the audit estimates 40%+ of the codebase).

---

## 10. Phased roadmap

Each phase = its own spec → implementation plan → build. Ordered by dependency (auth/infra before monetization/claim; remodel before SSR rendering of the new model).

| Phase | Scope | Notes |
|---|---|---|
| **0 — Modernize foundation** | Verified security fixes (hardcoded `SECRET_KEY` fail-fast, investment IDOR, search filter/`delete_data` bugs, `expire_all_by_user_id`); Python 3.14 + full dep overhaul; Typesense server v26→v30.2 (stepwise, snapshot) + client 2.0; GitHub Actions CI (ruff + pytest); non-destructive reindex CLI | Get the dormant app booting cleanly on a modern base. No new features. |
| **1 — Strip + remodel** | Delete the dead platform (§9); consolidate to Person/Org/Affiliation + investor_profile + polymorphic facets + geography + rich fields; collapse to one Typesense collection; Alembic migration + data backfill | The heart of the pivot. |
| **2 — SSR + SEO engine** | Jinja SSR for all public pages; one base layout; htmx/Alpine sprinkles; programmatic facet pages; JSON-LD; sitemaps/robots; Core Web Vitals | Remove Vue SPA fully here. |
| **3 — Infra swaps + auth** | Resend + magic-link auth (+ `login_tokens`); R2 storage (+ GCS migration); Cap captcha | Auth/email needed before monetization & claim. |
| **4 — Monetization** | Ads (house/sponsor slots) + Paddle Pro/lifetime + entitlement + webhook | Free-vs-Pro feature split. |
| **5 — Claim flow** | Rework claiming on the new model + Cap + magic-link; verified badge | Growth/freshness loop. |
| **6 — Data collectors** | EDGAR + Crunchbase ODM + registries → raw → entity resolution → canonical → Typesense; scheduled cadence | Ongoing freshness. |

---

## 11. Decisions log

**User decisions:** investors/firms hero (startups thin); ads + cheap Pro tier (~$7/mo + lifetime); keep claim + bookmarks/saved-searches/alerts + admin console; drop public crowdsourcing; Flask+Jinja SSR; magic-link only (drop all OAuth); Paddle (drop Stripe, no migration); Resend; R2; drop Pub/Sub; Cap captcha; Python 3.14; full dep bump; **Gemini embeddings**; public-domain data sources first; master doc + per-phase specs.

**Defaults taken (vetoable):** NL search deferred past v1; magic-link stateful tokens; Paddle one product / two prices; polymorphic facet joins; `fund` entity deferred; house/sponsor ads before AdSense; bookmarks free / other Pro features gated.

---

## 12. Open items & risks to verify at build time

- **Post-cutoff versions** (research-sourced, re-validate when implementing): Typesense server v30.2 / client 2.0.0, Paddle SDK 1.14.1, Resend SDK 2.32.2, Python 3.14 wheel availability for all deps.
- **Typesense v30 breaking change:** synonyms/curation moved to global top-level resources (`/synonym_sets/*`, `/curation_sets/*`) — any management code must use the new API. Snapshot before the multi-major upgrade (downgrade unsupported).
- **Gemini embeddings:** confirm exact model id and Typesense remote-embedder config for Google; budget per-query cost/latency; privacy note for anonymous traffic.
- **Exact enum strings** (Crunchbase/OpenVC) and **SEC dataset schemas** (Form D/ADV/13F) — verify against live sources before writing parsers.
- **Paddle** effective fee (~7% w/ FX) and small-txn terms — confirm with sales.
- **Resend** rate limit (2/s vs 5/s docs conflict) — confirm in dashboard.
- **Geocoding** replacement for `googlemaps` (Nominatim/geopy usage limits) if geography enrichment needs it.
