# Globalify Pivot — Research Brief for Spec Integration

This brief synthesizes 7 research tracks into spec-ready decisions. Version numbers, breaking changes, and low-confidence items are flagged explicitly. All facts as of 2026-06-22; the assistant knowledge cutoff is Jan 2026, so anything dated after that is research-sourced and tagged.

---

## 1. Typesense

**Current state:** server **v26.0**, python client **0.21.0** — both several majors behind.
**Target:** server **v30.2** (GitHub "Latest" badge), python client **2.0.0**.

### Upgrade path (in-place, stepwise)
Upgrades are in-place: install new binary/image, restart, Typesense rebuilds in-memory indices from disk — **no document reindex required** ([updating-typesense](https://typesense.org/docs/guide/updating-typesense.html)). But downgrades only span ~2 majors, so a multi-major jump is **not reversibly rollback-able** — **snapshot first**.

Step through majors, gating on `/health` 200 between each: **v26 → v27 → v28 → v29 → v30.2**.

Breaking changes to watch at each step:
- **v27.0** (2024-08-27): `facet_stats.total_values` now computed only over returned results; set `facet_strategy: exhaustive` if you need dataset-wide facet counts ([v27.0 notes](https://github.com/typesense/typesense/releases/tag/v27.0)).
- **v28.0** (2025-02-18): **no breaking changes** ([v28.0 notes](https://github.com/typesense/typesense/releases/tag/v28.0)).
- **v29.0** (2025-06-30): tightened schema validation — **documents with null in non-optional fields may fail to load; reindex from Postgres to remediate**. `group_by` `found` became approximate (~2%) ([v29 API](https://typesense.org/docs/29.0/api/)).
- **v30.0** (2026-01-27, **post-cutoff**): the disruptive one. Synonyms and curation/overrides moved from collection-scoped to **GLOBAL top-level resources** — `/collections/{c}/synonyms/*` → `/synonym_sets/*`, `/collections/{c}/overrides/*` → `/curation_sets/*`. Existing data **auto-migrates on upgrade (irreversible — snapshot first)**, but any client code that *manages* synonyms/overrides must be rewritten to the new API ([v30.0 notes](https://github.com/typesense/typesense/releases/tag/v30.0)).

### Python client bump
0.21.0 → **2.0.0** (released 2026-02-16, **post-cutoff**). Full typed rewrite, adds `AsyncClient`, requires **Python ≥3.9**, **targets server ≥v30.0** — so client and server must move to v30 **in lockstep** ([typesense-python](https://github.com/typesense/typesense-python)). Pairing 0.21.0 with a v30 server, or 2.x with v26, is unsupported. Migrating the client is a breaking change for `vector_query`/synonym/analytics call sites — validate signatures against the running server.

### New search features worth adopting (all need v28–v30)
- **Hybrid search + `rerank_hybrid_matches:true`** (v28) — every hit gets both text-match and vector scores via Rank Fusion. **Adopt for the main search box** (founders mix exact terms + intent queries).
- **Decay functions in `sort_by`** (gaussian/linear/exp, v28) — recency boost (last-active/last-deal) and geo-distance ranking. **Adopt (low effort).**
- **Global Synonym Sets + Curation Sets** (v30) — encode investor synonyms (VC=venture capital, angel aliases, stage/sector phrasings); pin canonical firms for high-value SEO queries.
- **Faceting controls** — `facet_strategy` (v27), `facet_sample_slope` + dynamic `facet_return_parent` (v30) for high-cardinality facets (sector/stage/geo/check-size).
- **Union/merge search across collections** (v28) + dedup/pinning (v30) — federate firms + people + funds.
- **Natural Language Search** (v30) — LLM turns "seed fintech VCs in Berlin <$2M" into `filter_by`/`sort_by`; schema prompt cached 24h. **Optional "ask in plain English" entry point**; requires external LLM key (OpenAI/Gemini/vLLM), so factor cost/latency/privacy for anonymous SEO traffic.
- **Defer for v1:** conversational RAG (LLM cost/latency, secondary to faceted browse) and image search (not relevant to investor data).

**Embeddings caveat:** built-in `ts/` catalog is still 2022–23 era (`ts/all-MiniLM-L12-v2` is the only model named in current docs). For best semantic quality, use an **external embedding model** (OpenAI `text-embedding-3`, or self-hosted GTE/BGE/e5) and keep MiniLM as a zero-dependency fallback. Issue [#2477](https://github.com/typesense/typesense/issues/2477) requests SOTA built-ins with no maintainer commitment.

**Low-confidence flags:** exact dates for minors (v27.1, v29.1, v30.1, v30.2) and the precise v30.2 release date (~Apr 2026) are medium confidence. v30 new-param names (`truncate`, `group_max_candidates`, MMR) came via search summaries — verify against the v30.0 release body. No formal 0.21→2.0 client CHANGELOG was retrieved.

---

## 2. Recommended data model

**Decision: YES — consolidate.** Replace the two parallel, duplicated `Investor` (person, with denormalized `firm_name` string) and `InvestmentFirm` (org) tables — plus their 6 duplicated M2M facet tables and duplicated Typesense sync — with a **Person + Organization + Affiliation** model.

**Why:** every reference platform separates people from orgs and links them with an explicit role edge: Crunchbase uses **Person / Organization / Job / Fund / FundingRound**, where a single Organization is differentiated by roles/facet_ids (company vs investor vs school — **not a table per kind**), and Person↔Org is the time-bounded **Job** entity ([Crunchbase Data Dictionary](https://data.crunchbase.com/docs/data-dictionary)). PitchBook mirrors this (Company/Investor/Fund/Deal + separate Professionals dataset, [PitchBook](https://pitchbook.com/platform-data/professionals)). Signal/NFX even models **solo angels as "firms" with partner People underneath**, each with their own check-size sweet spot ([Signal](https://signal.nfx.com/firms/angel-investor)). Globalify's current `firm_name` string and twin tables are exactly the anti-pattern these systems evolved away from.

### Core tables
- **organization** — id, slug (UNIQUE), name, org_type (enum), `is_investor` BOOL (fast discriminator/facet), about, website/linkedin/twitter/email/phone, hq_location, country, coordinates, founded_year, n_employees, aum, is_public, is_approved, search_index, timestamps.
- **person** — id, slug (UNIQUE), first/last/full_name, about, headline (current title for display), website/socials/contact, location, country, person_type (enum, nullable), user_id FK (nullable), is_public, is_approved, search_index, timestamps.
- **affiliation** (the firm↔partner edge, replaces `firm_name` string) — person_id FK, organization_id FK, title, role (enum), is_current, started_on/ended_on, is_lead, UNIQUE(person_id, organization_id, title). Mirrors Crunchbase **Job**; supports partners moving firms, multiple partners/firm, person who is both angel and partner.
- **fund** (optional, add later for AngelList/PitchBook-style vehicles) — slug, name, organization_id FK (owner), lead_person_id FK (nullable, syndicate/rolling-fund lead), fund_type (enum), vintage_year, target_size, money_raised, status.
- **investor_profile** (shared investment criteria, polymorphic — so an angel-person and a firm carry thesis without column duplication) — subject_type ('person'|'organization'), subject_id, min_check, max_check, sweet_spot, thesis, leads_rounds, n_investments, n_exits, UNIQUE(subject_type, subject_id). *(Or nullable columns directly on person/org to keep it simpler at small scale.)*
- **Polymorphic facet joins** — replace the 6 duplicated M2M tables with 4 shared: `entity_industry`, `entity_round/stage`, `entity_geography`, `entity_notable_investment`, each keyed `(subject_type, subject_id, <facet>_id)`.
- **geography** (id, name, slug, type country/region/city, country_code) — replaces free-text location strings; powers `/investors/london` geo SEO pages with stable slugs.
- **investment** — repoint to a single investor entity: `(investor_subject_type, investor_subject_id)` instead of today's separate `investor_id` + `investment_firm_id` columns.

### `org_type` enum
`vc_firm | angel_group | corporate_vc | family_office | accelerator | incubator | startup_studio | pe_firm | micro_vc | growth_equity | lp_fund_of_funds | syndicate | other`
`person_type`: `angel | partner | operator | scout | lp`. `affiliation.role`: `founder | gp | partner | principal | associate | scout | advisor | lp | operator`.

### ASCII sketch
```
        ┌──────────────┐         ┌──────────────────┐
        │   person     │         │  organization    │
        │ id, slug     │         │ id, slug         │
        │ headline     │         │ org_type (enum)  │
        │ person_type  │         │ is_investor      │
        └──────┬───────┘         └────────┬─────────┘
               │                          │
               │   ┌──────────────────┐   │
               └──<│  affiliation      │>──┘
                   │ person_id  FK     │
                   │ org_id     FK     │  title, role,
                   │ is_current        │  started/ended_on
                   └──────────────────┘
        ┌──────────────────────────────┐
        │ investor_profile (polymorph) │  subject_type/id
        │ entity_industry / _stage /   │  → person OR org
        │ _geography / _notable (M2M)  │
        └──────────────────────────────┘
   fund ──owner FK──> organization ; fund.lead_person_id ──> person
   investment ──(investor_subject_type, investor_subject_id)──> person|org
```

### Typesense projection
**Collapse the two collections into ONE** (`investors`/`entities`) with an `entity_type` ('person'|'organization') facet. For an SEO-first directory, every programmatic facet page (`/investors/fintech`, `/investors/seed/london`, `/angels/climate`) becomes **one filtered query over one schema and one URL template**; firm docs carry `partner_names[]`, person docs carry `affiliated_firm_name/slug`. Tradeoff: relevance tuning differs for person-name vs firm-name fields, and type-specific pages need an `entity_type` filter — a known cost, not a blocker.

**Migration path:** (1) create person/org from the two tables minus `firm_name`/facets; (2) for each `Investor.firm_name`, fuzzy-upsert an organization and insert an affiliation (title=position); (3) move M2M facets into polymorphic joins; (4) repoint investment FKs; (5) collapse the two Typesense collections; (6) drop old tables + 6 join tables.

*Caveat:* polymorphic `(subject_type, subject_id)` joins trade DB-level FK integrity for fewer tables; if strict FKs matter, use two nullable FK columns instead. Crunchbase exact enum strings could not be fully fetched (403s) — verify against the live Data Dictionary if exact parity is needed.

---

## 3. Field set

Grouped attributes; **★ = make a programmatic-SEO facet.** Store as flat fields + multi-valued tag tables. Taxonomy converges across Crunchbase (~14–24 types), OpenVC (~9 buckets, [investor-lists](https://www.openvc.app/investor-lists/)), NFX Signal.

**Classification**
- `investor_type` ★ (single canonical enum, ~20–24 values, Crunchbase-aligned) — `angel, angel_syndicate, angel_group, scout, micro_vc, vc_firm, growth_equity, corporate_vc, accelerator, incubator, venture_studio, family_office, private_equity, venture_debt, crowdfunding_platform, grant_program, government_program, search_fund, fund_of_funds, limited_partner, hedge_fund, secondary_buyer, investment_bank, endowment_foundation`. **Map to OpenVC's coarser ~9 public buckets for landing pages.**
- `is_firm` (bool), logo_url, `stages[]` ★ multi (`idea, pre_seed, seed, series_a…d_plus, growth, late_stage, pre_ipo, debt, secondary`), `sector_focus[]` ★ multi (fintech/ai_ml/climate/saas/… `sector_agnostic`), `geo_focus[]` ★ multi + structured `hq_location {city★, region, country★, country_code, lat/lng}`.

**Investment criteria**
- `check_size_min_usd` / `check_size_max_usd` ★ — **store as numeric min/max integers, NOT buckets**; derive display bands (<$25K … $10M+) at query time so range facets generate without remodeling. `sweet_spot_usd`, `fund_size_usd`, `fund_number`, `vintage_year`, `aum_usd`.
- `lead_preference` ★ (`lead | follow | both | unknown`), `thesis_summary`.

**Activity**
- `num_investments`, `num_lead_investments`, `num_exits`, `last_investment_date` (freshness/recency-boost signal), `recent_deals[]` (date+company+round), `portfolio_company_ids[]`, `notable_investments[]`, `co_investors[]` (linked), `is_active`.

**Contact** (high-conversion)
- `accepts_cold_inbound` ★, `application_url`, `accepts_application_form` ★, `contact_channels {email, linkedin, twitter, calendly, contact_form_url}`, `response_policy`, `partners[] {name, title, role, linkedin}` (decision-makers).

**Content / provenance** (E-E-A-T)
- `data_source` (crunchbase|openvc|nfx|manual), `verified` (bool), `verified_at`, `claimed_by_investor` (bool), `updated_at`.

**Highest-volume SEO facets are the cross-products** founders search: TYPE×STAGE (`/seed-investors/...`), TYPE×SECTOR (`/fintech-angel-investors`), STAGE×GEO (`/pre-seed-investors/berlin`), SECTOR×GEO — mirroring OpenVC's `/investor-lists/<facet>` URL pattern. Lower-volume/high-intent: lead-vs-follow, accepts-cold-inbound, check-size band.

*Caveats:* OpenVC/Crunchbase pages 403 to automated fetches — verify exact enum spellings against live UIs before freezing. Check-size ranges per type are directional market conventions, store as hints not constraints. `accepts_cold_inbound`/`application_url` coverage will be sparse on import (needs crowd/manual enrichment).

---

## 4. Data collectors

**Layered by legal cleanliness, cheapest/safest first.**

### Source priority
1. **SEC EDGAR — primary free backbone.** Form D (issuers + related persons), Form ADV (advisers/ERAs incl. VC/PE managers, AUM, CRD/CIK), 13F. Public-domain, official submissions JSON API + quarterly bulk datasets, **no ToS/copyright risk**. Requires descriptive **User-Agent** and **≤10 req/s** ([accessing-edgar-data](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)). Gives authoritative legal identities + dedup keys (CIK/CRD) but **no thesis/stage/portfolio** data; US-only. Effort: L.
2. **Crunchbase Open Data Map** — free with attribution (name, short description, logo, location, social links) ([ODM](https://about.crunchbase.com/blog/open-data-map/)). Legitimate seed skeleton. **Do NOT pay for the full API initially** (free tier gone in 2025; full API ~$50k+/yr, Enterprise-only). Add paid Crunchbase/Dealroom only if VC-narrative ROI is proven.
3. **Legal-entity registries** for dedup backbone — OpenCorporates (200M+ entities; free for open-data under share-alike, commercial from ~£2,250/yr), UK Companies House (free), EU BRIS.

### Restricted — do NOT scrape; use sanctioned APIs/partnerships only
**OpenVC** (opt-in founder directory — redistributing opt-in records risks ToS breach + GDPR on individual angels), **Wellfound/AngelList** (no public data API), **Product Hunt** (maker fields redacted since 2023, non-commercial default — email for commercial). These are opt-in/login-gated personal data; scraping conflicts with the "open" brand and creates GDPR/CCPA exposure.

### Legal posture
Post **hiQ v. LinkedIn** (9th Cir., narrow CFAA for public data) and **Meta v. Bright Data** (2024 SJ: browsewrap binds only logged-in users), scraping **logged-out PUBLIC** pages is generally defensible under CFAA in the 9th Circuit — but **contract/ToS (post-login), DB copyright, and GDPR/CCPA on personal data remain real risks**. Rules: descriptive User-Agent, honor robots.txt + per-domain rate limits, scrape only logged-out pages, never bypass auth, keep a per-source ToS/legal register. *Not legal advice; EU sui generis DB rights + GDPR change the EU calculus — get counsel before redistributing personal data.*

### Tooling (match cost to need)
`httpx` for APIs/static HTML → **Scrapy or crawlee-python** for scaled crawl (crawlee adds native Playwright + fingerprinting + proxy rotation) → **Playwright only for JS-heavy targets** (headless is ~5–20× costlier) → **Firecrawl/Crawl4AI/ScrapeGraphAI** LLM-extraction for low-volume adaptive layouts.

### Architecture
```
per-source collector workers (APIs first, scraping where allowed)
        → raw immutable landing tables in Postgres (source, fetched_at, payload)
        → normalize / entity-resolve  [Splink: probabilistic, ~1M rec/min on DuckDB,
            scales 100M+ via Spark; block on CIK/CRD/domain/normalized-name]
            (or dedupe lib via active learning if no labels)
        → canonical Postgres tables
        → incremental upsert → Typesense (v30.2)
```
**Cadence:** EDGAR daily (Form D/ADV) + quarterly bulk refresh; registries weekly/monthly; **news/RSS hourly** for funding-round freshness (feeds "recently active" SEO signal). Schedule via cron/APScheduler/Celery beat or a workflow engine. Separate raw vs canonical for reprocessing + provenance.

*Caveats:* Crunchbase/Dealroom pricing is from secondary blogs — confirm with sales. SEC dev pages 403'd the fetcher; verify Form D/ADV/13F dataset schemas on sec.gov before building parsers. Wellfound API status inferred.

---

## 5. Billing (Paddle)

**Feasibility: YES** — Paddle Billing (current product, replaces Classic) supports both a recurring **$7/mo** subscription and a one-time **"lifetime"** purchase. Model is **Product → Price**, one product with multiple prices: monthly = price with `billing_cycle {interval:month, frequency:1}`; lifetime = separate one-time price with **`billing_cycle: null`** ([create-products-prices](https://developer.paddle.com/build/products/create-products-prices)). **Critical:** a one-time purchase does **NOT create a subscription** — lifetime entitlement must be granted off the **transaction**, not a subscription object.

### Entitlement / webhook flow (webhooks = source of truth, NOT the JS callback)
- Frontend: Paddle.js v2 (`cdn.paddle.com/paddle/v2/paddle.js`), `Paddle.Initialize({token})`, `Paddle.Checkout.open({items:[{priceId, quantity}], customData:{user_id}})`. **Overlay** checkout as default. `customData` maps Paddle records back to your DB user (Billing-era replacement for Classic's `passthrough`) and is copied onto the subscription when created ([custom-data](https://developer.paddle.com/build/transactions/custom-data)).
- Flask endpoint `POST /webhooks/paddle`: read **raw body** before any JSON parse, verify, dispatch, return 200 fast.
- Handlers: **`transaction.completed`** → if items include the lifetime price, grant permanent access by `customData.user_id`; **`subscription.created`/`activated`** → store customer_id + subscription_id + current_period_end, grant; **`subscription.updated`** (catch-all: renewals/upgrades/pauses/resumes) → reconcile; **`subscription.canceled`** → revoke at period end ([webhooks overview](https://developer.paddle.com/webhooks/overview)).
- **Idempotency required** — Paddle re-delivers/retries; dedupe on `event_id`, treat grant/revoke as upserts.

### Signature verification
`Paddle-Signature` header = `ts=<unix>;h1=<hex>`; `signedPayload = ts + ':' + rawBody` (**unmodified raw body — do not re-serialize**); HMAC-SHA256 with destination secret; timing-safe compare; reject drift >tolerance (SDK default 5s) ([signature-verification](https://developer.paddle.com/webhooks/signature-verification)). SDK: `Verifier().verify(request, Secret(WEBHOOK_SECRET))`.

### MoR / tax
Paddle is **Merchant of Record** — auto-calculates/adds VAT/GST/US sales tax at checkout by buyer location, remits to 100+ jurisdictions, issues compliant invoices, absorbs chargebacks/fraud ([how Paddle handles VAT](https://www.paddle.com/help/sell/tax/how-paddle-handles-vat-on-your-behalf)). **You do not register or file foreign tax returns.** Remove any self-managed/Stripe Tax logic; accounting expects **net payouts**. Cost: **5% + $0.50/txn** all-inclusive, ~7% effective with FX margin (medium confidence — confirm with sales).

### Python integration
Official **`paddle-python-sdk`** (PyPI v1.14.1, 2026-04-21 — **post-cutoff**), **requires Python ≥3.11** ([PyPI](https://pypi.org/project/paddle-python-sdk/)). **⚠ Verify the Flask runtime is ≥3.11 — this is the most likely install blocker.** If pinned lower, either bump Python or call the REST API directly (`api.paddle.com` / `sandbox-api.paddle.com`, Bearer token) and verify signatures manually with `hmac`/`hashlib`. Test end-to-end in **sandbox** (client token + API secret + notification destination + test cards, tunnel webhooks via ngrok/Hookdeck) before going live.

### Stripe migration
Concepts map cleanly (Product→Product, Price→Price, Customer→Customer, Checkout Session→Paddle.Checkout, `metadata`/`client_reference_id`→`customData`, Stripe-Signature→Paddle-Signature). **You CANNOT migrate live Stripe card tokens** (different processors/PCI scope) — existing subscribers must re-enter payment via a Paddle checkout. **Plan a parallel-run cutover**, migrate subscribers by re-subscribe, then cancel the Stripe sub.

---

## 6. Email (Resend) & Storage (R2)

### Resend
Official **`resend`** PyPI (v2.32.2, 2026-06-17 — **post-cutoff**, Python 3.7+). Send is a one-liner: set `resend.api_key`, build `SendParams {from,to,subject,html}`, `resend.Emails.send(params)` ([send-with-python](https://resend.com/docs/send-with-python)). **No server-side templating** — render Flask Jinja2 templates to an HTML string and pass as `html` (React Email is Node/TS, not usable from Python).

- **Module:** `src/project/utils/email/resend_client.py` — `send_email(to, subject, html, from_addr='Globalify <noreply@mail.globalify.com>')`, bodies via `render_template('email/*.html', **ctx)`, plus a retry wrapper honoring 429 + `ratelimit-reset`.
- **Deliverability:** verify a **sending subdomain** (`mail.globalify.com`) — add generated SPF TXT + bounce MX + DKIM TXT, and a DMARC TXT (`p=none` → `quarantine`). **Do not send from the root domain.** ([domains intro](https://resend.com/docs/dashboard/domains/introduction))
- **Rate limit:** default ~**2 req/s per team** (raisable) — bulk alerts must throttle/queue. *Low confidence: docs vs changelog show conflicting 2/s vs 5/s; confirm in dashboard.*
- **Pricing:** Free 3,000/mo (100/day cap, 1 domain); Pro $20/mo (50,000, 10 domains, no daily cap). Re-check at purchase.

**Magic-link auth (also covers claim-verification + alerts via a `purpose` discriminator):**
- **Option B (preferred, stateful):** `secrets.token_urlsafe(32)`; store `sha256(token) + user_id + purpose + expires_at + consumed_at` in a Postgres `login_tokens` table. Email `https://globalify.com/auth/verify?token=…`; on click validate → check unexpired+unconsumed → mark consumed → `flask_login.login_user(user)`. Allows revocation + auditability for the "claim a VC firm" flow.
- Option A (stateless): `itsdangerous URLSafeTimedSerializer` with short `max_age` (e.g. 600s) — simpler, no revocation.

### Cloudflare R2 (S3-compatible via boto3)
- **Client:** `endpoint_url=https://<ACCOUNT_ID>.r2.cloudflarestorage.com`, `region_name='auto'`, service `s3`. **API token → S3 creds:** Access Key ID = token id; **Secret = SHA-256 of token value (shown once)**; scope to "Object Read & Write" per bucket ([R2 tokens](https://developers.cloudflare.com/r2/api/tokens/)).
- **Headline win:** **R2 egress is FREE** (vs S3/GCS ~$0.08–0.12/GB) — decisive for SEO image serving. Storage $0.015/GB-mo; free tier 10GB + 1M Class A + 10M Class B ([pricing](https://developers.cloudflare.com/r2/pricing/)).
- **Public serving:** do **NOT** use `r2.dev` in production (rate-limited, dev-only, not a valid CNAME target). Attach a **Custom Domain** (`img.globalify.com`) on a Cloudflare-managed zone → CDN caching + WAF + free egress. Add a Cache Everything rule for image paths ([public-buckets](https://developers.cloudflare.com/r2/buckets/public-buckets/)).
- **S3 incompatibilities:** **no ACLs** (`x-amz-acl` ignored — public access is bucket/custom-domain-level, not per-object), no bucket policies, no versioning/replication, no object tagging/locking, no AWS-managed SSE/KMS (SSE-C ok); only STANDARD/STANDARD_IA.

**GCS → R2 image-pipeline swap:** the existing `google_storage.py` Pillow/pillow-heif processing (HEIC decode, RGBA→RGB flatten, 100×100 avatar crop, scale-to-HD 1280×720, JPEG) is **storage-agnostic — keep verbatim.** Only swap the I/O layer:
- New `src/project/utils/r2/r2_storage.py` mirroring `upload_blob`/`delete_blob`/`download_blob` via `put_object`/`delete_object`/`get_object`.
- Replace `blob.public_url` with `f"https://{R2_PUBLIC_DOMAIN}/{key}"`. **Store only the UUID key in Postgres, not the full URL**, and compute URLs at render time (decouples backend; current `delete_blob_from_url` URL-parsing is brittle). Audit call sites: `settings.py`, `admin/user.py`, `admin/company.py`.
- For browser-direct uploads (logo claims): presigned PUT via `generate_presigned_url('put_object', Params={Bucket,Key,ContentType}, ExpiresIn=900)`; client must send the **exact** Content-Type or get 403 SignatureDoesNotMatch. Keep private originals in a non-public bucket, serve via presigned GET.
- **Data migration:** one-off script lists GCS blobs → `put_object` to R2 preserving UUID key → verify counts/hashes → backfill DB to keys → cut over → delete GCS bucket. (Effort: L.)

---

## 7. Open decisions

**Owner must decide:**
1. **Python runtime version** — Paddle SDK needs ≥3.11, Typesense client 2.x needs ≥3.9. Confirm/bump the Flask runtime; if <3.11, decide SDK-vs-REST for Paddle. **Blocks billing.**
2. **External embedding provider vs built-in MiniLM** — better semantic quality + LLM cost/privacy for anonymous SEO traffic, vs zero-dependency MiniLM fallback.
3. **Adopt Natural Language Search in v1?** — UX differentiator but adds per-query LLM cost/latency/privacy review.
4. **investor_profile: polymorphic table vs nullable columns** on person/org (fewer tables vs DB-level FK integrity). Same tradeoff for the facet joins.
5. **Fund entity now or later** — recommend later (don't block the People/Org/Affiliation refactor); reserve the type so funds aren't crammed into Organization.
6. **Same Product vs separate Products** for the $7/mo and lifetime prices (affects Paddle reporting/checkout UX; both supported).
7. **Stripe cutover timing** — parallel-run window length; subscriber re-subscribe campaign.
8. **Magic-link: stateful vs stateless tokens** (recommend stateful for revocation + claim flows).
9. **Paid Crunchbase/Dealroom tier** — only if VC-narrative ROI proven; ODM + EDGAR cover v1.

**Conflicting / uncertain findings to verify before freezing spec:**
- Resend default rate limit (**2/s vs 5/s** — docs vs changelog conflict).
- Paddle effective fee (~7% with FX) and exact small-txn/enterprise terms — confirm with sales.
- Typesense minor-release dates (v27.1/v29.1/v30.1/v30.2) and v30 new-param names — medium confidence, verify against release bodies.
- Crunchbase/OpenVC exact enum strings — pages 403 to fetchers; verify against live UIs.
- SEC Form D/ADV/13F dataset field schemas — sec.gov 403'd; verify before building parsers.
- Crunchbase/Dealroom 2026 pricing — from secondary blogs; confirm with sales.
- **Post-cutoff items** (research-sourced, not in training data): Typesense v30.x + client 2.0.0, Paddle SDK 1.14.1, Resend 2.32.2. Re-validate versions at implementation time.