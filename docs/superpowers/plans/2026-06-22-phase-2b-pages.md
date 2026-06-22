# Phase 2b — Entity Profiles + Browse Pages (SSR core)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Real server-rendered `/investors`, `/investors/<slug>`, `/firms`, `/firms/<slug>` reading the new Person/Org model — the actual product surface — with Person/Organization/ItemList/BreadcrumbList JSON-LD, Pro-gated contact, and 301s from legacy URLs.

**Architecture:** A new public, SSR-only `public` blueprint. Browse pages query Typesense via `entity_search.get_search` (paginated); profile detail pages read Postgres directly (the entities doc omits phone/per-affiliation/thesis/geo-names). All pages extend `base.html` and emit JSON-LD via the 2a partials. Design reference: **`docs/phase-2-planning-brief.md` §1 (2b), §2, §3**.

**Tech Stack:** Flask + Jinja SSR, SQLAlchemy (profile bundles), Typesense v30 `get_search` (browse), Playwright (verify).

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never `main`.
- **SSR + crawlable:** content in server HTML, extends `base.html`, sets `title`/`meta_description`/`canonical` blocks. No Vue. htmx sprinkles are 2e — pages must be complete without JS.
- **Pro-gated contact (spec §5):** locked contact (email/phone) for non-Pro/anonymous users must NOT be emitted into the HTML at all (gate at render, omit from DOM) — not hidden with CSS.
- **No N+1 in the request path:** `load_profile_bundle` fetches affiliations/profile/facets with grouped `IN`/`select` queries, not per-row loops. (The batch N+1 in `sync_search_index` is fine; the request path is not.)
- **`InvestorProfile`/`entity_*` are polymorphic** `(entity_type, entity_id)` with NO ORM relationship — query with explicit `db.select(...).where(entity_type==X, entity_id==id)`.
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run pytest` green; `uv run ruff check . && uv run ruff format --check .` clean; app imports. Playwright where stated.
- **Commits:** conventional subject; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: Model query helpers (`get_by_slug` + `load_profile_bundle`)

**Files:** `src/project/models/entity.py` (add staticmethods/classmethods), `tests/test_entity_queries.py`.

**Interfaces (produced):**
- `Person.get_by_slug(slug: str) -> Person | None` — filters `is_public=True`.
- `Organization.get_by_slug(slug: str) -> Organization | None` — filters `is_public=True`.
- `load_profile_bundle(entity_type: EntityType, entity_id: int) -> dict` returning `{"profile": InvestorProfile|None, "industries": list[Industry], "stages": list[InvestmentStage], "geographies": list[Geography], "notables": list[NotableInvestment], "affiliations": list[Affiliation]}` (for a Person: affiliations = orgs they're affiliated with; for an Organization: affiliations = its partner people). Use grouped queries (one query per facet kind, joined to the lookup table), not per-row.

- [ ] **Step 1:** Read `entity.py` for the exact column names + the `(entity_type, entity_id)` shape on `InvestorProfile`/`EntityIndustry`/`EntityStage`/`EntityGeography`/`EntityNotable`, and `Affiliation` (`person_id`/`organization_id`).
- [ ] **Step 2:** Write `tests/test_entity_queries.py` FIRST — seed a Person + Organization + Affiliation + InvestorProfile + one of each `entity_*` facet (under the `app` fixture + `db.create_all()`); assert `get_by_slug` returns the public entity (and None for a non-public/missing slug), and `load_profile_bundle` returns the profile + the linked industries/stages/geographies/notables + affiliations with NO extra queries per facet (assert correctness of contents). Run → fail.
- [ ] **Step 3:** Implement the helpers in `entity.py` (grouped `db.select` joins; `is_public` filter on `get_by_slug`).
- [ ] **Step 4:** Gate (pytest green incl. new tests + `test_db_metadata_creates_all_tables`; ruff; import).
- [ ] **Step 5: Commit** (`feat(model): add Person/Organization get_by_slug + load_profile_bundle`).

---

## Task 2: `public` blueprint + browse pages (`/investors`, `/firms`)

**Files:** create `src/project/routes/public.py`; register in `src/project/__init__.py`; create `templates/browse/list.html`, `templates/partials/_person_card.html`, `templates/partials/_org_card.html`.

- [ ] **Step 1:** Create `public` blueprint with `GET /investors` and `GET /firms`. Each parses filter/sort/page query params (reuse `search.py`'s param parsing where sensible), calls `entity_search.get_search(query, entity_type=PERSON|ORG, filters..., page, per_page=18)`, and renders `browse/list.html` with the hits + pagination context. `get_search` returns no `pages` — compute `(found + per_page - 1) // per_page`. Standardize `per_page` in one place.
- [ ] **Step 2:** `browse/list.html` (extends base): heading, a results grid of `_person_card`/`_org_card` (pick by `entity_type`), pagination controls (plain links with query params — JS-free), and a results count. Set `title`/`meta_description`/`canonical`. Emit ItemList + BreadcrumbList JSON-LD (2a partials) for the listed entities.
- [ ] **Step 3:** `_person_card.html` / `_org_card.html` — card markup from a search hit dict (name, headline/org_type, location, industries/stages chips, link to the profile slug). Replace the deleted Vue `full_investor`/`full_investment_firm` macros.
- [ ] **Step 4:** Register the blueprint; ensure `/firms` is PUBLIC (no `@login_required`). Keep the old `search`/investment-firm routes for now (legacy redirects come in Task 3).
- [ ] **Step 5:** Gate (pytest green incl. `test_no_url_for_to_unregistered_endpoints`; ruff; import). The browse routes need Typesense at runtime — they're not exercised by sqlite tests; verify via Playwright in Task 3's pass.
- [ ] **Step 6: Commit** (`feat(public): SSR /investors + /firms browse pages over entities search`).

---

## Task 3: Profile pages + JSON-LD + legacy redirects + Playwright verification

**Files:** add `GET /investors/<slug>` + `GET /firms/<slug>` to `public.py`; create `templates/profiles/person.html`, `templates/profiles/organization.html`; fill the JSON-LD partials with real data; add legacy 301 redirects.

- [ ] **Step 1:** Profile routes: `get_by_slug` → 404 if missing → `load_profile_bundle` → render `profiles/person.html`/`organization.html`. Pro-gate contact (emit email/phone only if the viewer is entitled — anonymous/non-Pro: omit from DOM). Set per-page `title`/`meta_description`/`canonical` (absolute https URL).
- [ ] **Step 2:** `profiles/person.html` / `organization.html` (extend base): name, headline/type, about/thesis, location, industries/stages/lead-pref/check-size, affiliations (person↔firm), notable investments, contact (gated). Emit Person/Organization + BreadcrumbList JSON-LD via the partials (fill them with real entity data).
- [ ] **Step 3:** Legacy 301 redirects (preserve query params): `/investor/<slug>` → `/investors/<slug>`, `/investment-firm/<slug>` → `/firms/<slug>`, `/search` → `/investors`, `/search/investment-firms` → `/firms`. (Add these where the old routes live or as new redirect routes; ensure `test_no_url_for_to_unregistered_endpoints` stays green.)
- [ ] **Step 4: Gate** (pytest green; ruff; import).
- [ ] **Step 5: Playwright verification (the milestone).** Seed sample data + run Typesense in Docker, then verify the real pages:
  - Start Typesense: `docker run -d --name ts-2b -p 18108:8108 -v /tmp/ts-2b:/data typesense/typesense:30.2 --data-dir /data --api-key=xyz --enable-cors`; wait for health.
  - Seed: with `_DATABASE_URL=sqlite:////tmp/p2b.db`, `_TYPESENSE_*` pointing at the Docker instance, `_TYPESENSE_EMBEDDER=minilm`, run `flask setup` (seeds catalog → backfill → `entity_search.sync_search_index(recreate=True)`). If `flask setup` is too heavy, seed a handful of Person/Org rows + run sync directly.
  - Run the app; with Playwright: `browser_navigate` to `/investors` (browse) and a real `/investors/<slug>` (profile); `browser_snapshot` confirms entity content renders; `browser_evaluate` parses `script[type="application/ld+json"]` and asserts `@type` is `ItemList`/`BreadcrumbList` on browse and `Person`/`Organization` on the profile; assert per-page `title` + `canonical`; assert locked contact is ABSENT from the anonymous DOM; `browser_console_messages` = 0 errors. `browser_take_screenshot` of a profile + the browse page.
  - Tear down: `docker rm -f ts-2b && rm -rf /tmp/ts-2b`.
- [ ] **Step 6: Commit** (`feat(public): SSR investor/firm profile pages, JSON-LD, legacy 301s`).

---

## Self-Review

**Coverage (brief §1 2b):** model helpers (T1) · public blueprint + browse (T2) · profiles + JSON-LD + redirects + Playwright (T3). 

**Deferred:** facet pages + sitemaps (2c), admin rewire + catalog drop (2d), htmx filter/bookmark sprinkles + magic-link (2e), home-page full rewrite (uses these cards — can refine in 2c/2e). Startup thin pages deferred (no model yet).

**Risk control:** profile detail reads Postgres (resilient to Typesense outage); browse degrades to empty list if Typesense is down (don't 500); N+1 avoided via `load_profile_bundle`; Pro contact omitted from DOM not CSS-hidden; every page extends base so SEO tags + JSON-LD are consistent. Playwright proves the real pages render with valid structured data before 2c builds facet pages on the same templates.
