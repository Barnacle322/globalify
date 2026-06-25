I'll produce the planning brief directly. This is a synthesis task over the provided scoping data — no file exploration needed since the scoping is already code-grounded with exact file/route references.

# Globalify Phase 2 — SSR + SEO Front-End: Implementation Planning Brief

## 0. Context & guiding constraints

Phase 1a removed the Vue **runtime** but left Vue **markup** in ~30 templates, so the data-rich pages render nothing crawlable. The new `Person/Organization/Affiliation/InvestorProfile/Geography + entity_*` models exist and feed a single Typesense `entities` collection via `entity_search.sync_search_index` / `get_search`, but **no route reads the new tables** and there are **no `get_by_slug` helpers**. Admin write routes are **actively broken** (they call `upsert_data()/delete_data()` that no longer exist). CSS build is broken (`node_modules` absent). These four facts shape the ordering below.

---

## 1. Sub-plan decomposition (ordered, independently shippable)

### 2a — Foundation: CSS build + base layout + SSR partials
**Goal:** One parameterized base layout, working Tailwind build, JSON-LD/partial scaffolding — the substrate every later sub-plan extends.

**Files touched:**
- `npm install`; verify `npx postcss src/project/static/static/src/input.css -o .../css/main.css` (committed `main.css` is a stale Feb-2025 118KB artifact).
- New `src/project/templates/layouts/base.html` (blocks: `title`, `meta_description`, `canonical`, `og`, `json_ld`, `content`, `scripts`).
- New partials: `partials/_nav.html`, `_footer.html`, `_head_meta.html`, `_analytics.html` (PostHog, behind config flag).
- New JSON-LD partials: `partials/_jsonld_person.html`, `_jsonld_organization.html`, `_jsonld_breadcrumb.html`, `_jsonld_itemlist.html`.
- Migrate salvageable pages onto base: `index.html`, `privacy_policy.html`, `terms_of_service.html`, `errors/{400,401,403,404,500,503}.html`, `auth/login.html`. Consolidate the 4 duplicated PostHog snippets + per-page `menu.js` includes.
- `tailwind.config.js`: drop dead `view-eric/jennifer/arstan` classes + dead animations (confirm content glob still scans `./src/project/templates/**/*.{html,htm}`).
- Delete `layouts/layout_app.html` (dead Vue shell) once nothing extends it (blocked until 2b/2d move `suggestions.html`, `settings/security.html`).

**Dependencies/order:** FIRST. Everything else extends `base.html`. CSS build must work before any visual verification.
**Risk:** Low–medium. Main risk is Tailwind purge dropping classes if the content glob is wrong — verify glob and regenerate `main.css` after each template batch.
**Verify:** `npm run css` succeeds; Playwright `browser_navigate` to `/`, `/privacy-policy`, `/404` then `browser_snapshot` (content present), `browser_console_messages` = zero errors (catches orphaned-Vue regressions), and `browser_evaluate` asserts `document.title` + `meta[name=description]` + `link[rel=canonical]` exist.

### 2b — Entity profiles + browse pages (the SSR core)
**Goal:** Real SSR `/investors`, `/investors/<slug>`, `/firms`, `/firms/<slug>` reading the **new** models. Collapse the JSON+Vue split.

**Files touched:**
- New blueprint `routes/public.py` (100% public, 100% SSR), registered in `src/project/__init__.py`.
- `models/entity.py`: add `Person.get_by_slug(slug)` / `Organization.get_by_slug(slug)` (filter `is_public`), plus a `load_profile_bundle(entity_type, id)` assembling `Affiliation`+`InvestorProfile`+`EntityIndustry/Stage/Geography/Notable` via grouped `IN`/`selectinload` (the per-row N+1 in `sync_search_index` is fine for batch, NOT for request path).
- New templates: `profiles/person.html`, `profiles/organization.html`, `browse/list.html` (shared by `/investors`+`/firms`+facets), card partials `partials/_person_card.html`, `_org_card.html` (replacing the Vue macros `full_investor.html`/`full_investment_firm.html`).
- Browse routes reuse `search.investor_search` filter parsing + `generate_pagination` over `entity_search.get_search` (note: `get_search` does NOT return `pages` — keep `found//per_page`; standardize `per_page=18`/`12` in one place).
- Profile detail reads **Postgres, not Typesense** (entities doc omits phone, per-affiliation title/role, thesis, geography names). Per spec §5, **locked Pro contact must not be emitted into HTML** — gate at render, omit from DOM.
- Make `/firms` + firm profiles PUBLIC — remove `@login_required/@check_user_info_complete/@check_verification` from `investment_firm_slug`.
- 301 redirects: `/investor/<slug>→/investors/<slug>`, `/investment-firm/<slug>→/firms/<slug>`, `/search→/investors`, `/search/investment-firms→/firms` (preserve query params).
- Emit Person/Organization + BreadcrumbList JSON-LD (2a partials); ItemList on browse.

**Dependencies/order:** After 2a (needs base layout + JSON-LD partials). Independent of 2d (reads new models that already exist additively).
**Risk:** Medium–high. N+1 on profile bundle; `InvestorProfile` uses `(entity_type, entity_id)` discriminator with **no ORM relationship** (must `db.select(...).where(entity_type==PERSON, entity_id==person.id)`); `EntityIndustry/Stage/Notable` need manual joins.
**Verify:** Playwright on `/investors`, `/investors/<slug>`, `/firms`, `/firms/<slug>`: `browser_snapshot` content present; `browser_evaluate` parses `script[type="application/ld+json"]` → `@type` Person/Organization/ItemList; assert locked contact NOT in DOM for anonymous; zero console errors.

### 2c — Programmatic SEO: facet pages + sitemaps + robots
**Goal:** Bounded, quality-gated facet URL surface + data-driven sitemaps + JSON-LD + canonical/noindex policy.

**Files touched:**
- New `utils/seo/slugs.py`: enum↔hyphen-slug codec (`pre_seed`↔`pre-seed`, `series_d_plus`↔`series-d-plus`, `vc_firm`↔`vc-firm`), single `SEO_FACETS` map (slug → `(facet_field, typesense_value)`), canonical-URL builder.
- `models/helpers.py`: add `Industry.slug` (unique, `python-slugify`) + Alembic migration + backfill; re-index `entities.industries[]` to slugs in `entity_search.py` (currently stores **names** at ~line 183) — **(a)** preferred over a slug→name lookup. `Geography.slug` already exists (zero transform).
- Facet registry (table or generated JSON) populated from Typesense `facet_counts`, gating which combos are 200 vs 404, canonical vs noindex (threshold ≥3–5 entities).
- One view `facet_page(segments)` for `/investors/<path:facet_path>` + `/firms/<path:facet_path>`: split → classify each segment (geo via `Geography.slug`, sector via `Industry.slug`, else hyphenated `InvestorType`/`InvestmentStage`/`OrgType`) → 404 unknown/registry-absent → one `get_search` call → set canonical+robots from registry → render `browse/list.html`. Enforce fixed segment order (type, stage/sector, geo); 301 mis-ordered combos.
- Replace `main.sitemap` (currently zero-arg `url_map` walk, can't emit `<slug>` URLs) with `<sitemapindex>` → `/sitemap-investors-N.xml`, `/sitemap-firms-N.xml` (Person/Org slugs where `is_public AND is_approved`, 50k/file chunks), `/sitemap-facets.xml` (registry `is_canonical=true`).
- Update `main.robots` (currently disallows removed OAuth paths): `Disallow: /admin /settings /login /claim /payment` + `Disallow: /*?*`, drop OAuth lines, point to sitemap index.

**Dependencies/order:** After 2b (needs `browse/list.html`, browse routing, JSON-LD partials). The `Industry.slug` migration can land early but re-indexing should coordinate with 2d's reindex helper.
**Risk:** Medium. Combinatorial URL explosion if registry not enforced; thin/empty pages must be `noindex,follow`; pagination `page=1` canonical, `page>1` `noindex,follow`.
**Verify:** Playwright on `/investors/seed/fintech`, `/investors/london`, `/firms/vc-firm`: assert `link[rel=canonical]` correct, ItemList+BreadcrumbList JSON-LD parse, robots meta on param URLs. Fetch `/sitemap.xml` and assert valid `<sitemapindex>`; fetch a child sitemap and assert real slugs.

### 2d — Admin/settings rewire + catalog drop
**Goal:** Fix broken admin writes onto the entity model, retire backup/restore/dedup, then drop old tables.

**Files touched (ordered STEP A→H):**
- **A** Move `NotableInvestment` out of `models/investor.py` → `entity.py`/`helpers.py`; repoint `entity_search.py` import (line ~120).
- **B** `admin/investor.py` writes (`create/update/approve/delete/filter_investors/search_notable_investments`) onto `Person`+`Affiliation`+`InvestorProfile`+`EntityIndustry/Stage/Geography/Notable` + per-entity reindex helper `entity_search.sync_one(type,id)` (don't full-sync per save). **Delete** `undo_investor_data`/`restore_investor_data`/`duplicates`/`merge_investors`.
- **C** `admin/investment_firm.py` writes onto `Organization`+`InvestorProfile`+`entity_*`; fix latent bug `rounds=Round.get_by_id_list(form_data.get('notable_investments'))`.
- **D** `admin/__init__.edit_claim_request` → `Person` via `ClaimRequest.(entity_type,entity_id)`, set `Person.user_id`. `settings.py` `index`/`edit_investor`/`investor_list_view`/`investment_firms_list_view` → `Person`/`Organization`; **delete** `investor_point_origin_data`/`restore_investor_data` + `InvestorOriginPointSchema`.
- **E** `routes/main.py` + `routes/search.py`: repoint off `Country`/`Investor`/`InvestmentFirm` → `Geography`/`Person`/`Organization`; replace `schemas/investor.py` with new-model schemas. (Overlaps 2b.)
- **F** `models/claim.py`: drop `investor_id` FK cols, `relationship('Investor')`, `get_with_investor_by_user_id`, `get_by_investor_id` (keep `entity_type/entity_id`).
- **G** `models/investor.py`: delete `Investor`/`InvestmentFirm`/`InvestorBookmark`/`InvestmentFirmBookmark`/`InvestorBackup`/`InvestorOriginPoint` + 6 M2M tables; strip `User` relationships (`investor`/`investor_backup`/`*_bookmarks`); update `models/__init__.py __all__`; rewrite/retire `backfill.py` + `__init__.py setup` CLI imports.
- **H** New Alembic revision `down_revision='c3d4e5f6a7b8'`, FK-safe drop order: claim FK cols → `investor_bookmark`, `investment_firm_bookmark`, `investor_backup`, `investor_origin_point` → 6 M2M → `investor`, `investment_firm` → `country` (after search repoint).

**Dependencies/order:** Writes (A–E) BEFORE drop (H) — dropping first breaks routes harder and loses backfill source. STEP E coordinates with 2b. `claim.py` (Phase 5) blocks full old-model retirement — but 2d only needs the legacy FK dropped, not the claim flow reworked.
**Risk:** High. `backfill_entities()` + `populate_demo`/`populate_vcsheet` are the last legitimate old-ORM consumers — retire only after prod data migrated; until then `flask setup` must seed the new model directly.
**Verify:** `flask db upgrade` + boot smoke test (import graph fails loudly if an import site missed) + `ruff` + `pytest`. Playwright on admin create/update/delete flows (logged-in) confirm 200 + reindex (search reflects change).

### 2e — htmx/Alpine sprinkles + filter UX + auth
**Goal:** Progressive enhancement over the SSR baseline; magic-link auth.

**Files touched:**
- Self-host `static/vendor/htmx.min.js` (~14KB, `defer`) — **no CDN**. Alpine only if a true client-state widget appears.
- Bookmark button: `<button hx-post=/bookmarks/{type}/{id} hx-swap=outerHTML>` returning toggled partial; CSRF via `hx-headers`. Re-key `EntityBookmark` on `Person/Organization` ids (currently old-model ids).
- Filter form: `<form method=get hx-get hx-target=#results hx-push-url=true>`; same Jinja partial serves full page + fragment (detect `HX-Request` header). Maps to existing `round[]/industry[]/country[]/min_investment/max_investment/sort_field`.
- Mobile menu: keep tiny `menu.js` or Alpine `x-data` (prefer fewer libs).
- Magic-link auth: strip OAuth from `auth/login.html` + `verify_email.html`; **delete** `settings/delete_oauth_account.html`. Rebind `claiming/*` to `Person/Org`.

**Dependencies/order:** LAST (enhances pages from 2b/2c). Bookmark re-keying depends on 2d (new-model ids).
**Risk:** Low–medium. Must degrade gracefully (full content with JS off).
**Verify:** Playwright: filter `<form>` submits via GET + updates URL params; `browser_network_requests` shows `HX-Request` header + `#results` swaps; bookmark toggle returns partial; second pass with JS disabled confirms content in initial HTML.

---

## 2. SSR page + route map

| Route | Method | Template | Source | JSON-LD |
|---|---|---|---|---|
| `/` (`main.index`) | GET | `pages/home.html` (rewrite) → base | static + links | — |
| `/investors` | GET | `browse/list.html` | `get_search(person)` | ItemList + Breadcrumb |
| `/investors/<slug>` | GET | `profiles/person.html` | Postgres `Person.get_by_slug` | Person + Breadcrumb |
| `/firms` | GET | `browse/list.html` | `get_search(org)` | ItemList + Breadcrumb |
| `/firms/<slug>` | GET | `profiles/organization.html` | Postgres `Organization.get_by_slug` | Organization + Breadcrumb |
| `/investors/<path:facet>` | GET | `browse/list.html` | facet `get_search` | ItemList + Breadcrumb |
| `/firms/<path:facet>` | GET | `browse/list.html` | facet `get_search` | ItemList + Breadcrumb |
| `/startups/<slug>` | GET | `pages/startup.html` | deferred (no model) | — |
| `/sitemap.xml` | GET | `seo/sitemap_index.xml` | DB-driven | — |
| `/sitemap-{investors,firms}-N.xml`, `/sitemap-facets.xml` | GET | `seo/sitemap_<seg>.xml` | DB slugs / registry | — |
| `/robots.txt` | GET | inline/`seo/robots.txt` | updated disallow set | — |
| `/privacy-policy`, `/terms-of-service`, errors, `/health` | GET | reparented to base | static | — |
| 301 legacy: `/investor/<slug>`, `/investment-firm/<slug>`, `/search`, `/search/investment-firms` | GET | — | redirect (preserve params) | — |

**Base-layout consolidation:** `layouts/base.html` replaces the 5 layouts + 7 self-heading top-level pages (`investor`, `investment_firm`, `search`, `search_investment_firms`, `history`, `privacy_policy`, `terms_of_service`) — resolves the ~11-head-duplication. `layout_app.html` deleted. `layout_auth.html`/`layout_clean.html`/`layout_error.html` fold into base variants. PostHog centralized in `_analytics.html` behind a `settings.posthog.key` flag.

**Blueprint plan:** new `public` blueprint owns the SSR surface; shrink `main` to health/sitemap/robots/errors; `search` keeps JSON typeahead + legacy redirects; `claim` untouched until Phase 5; `settings`/`admin` old-model reads retired in 2d.

---

## 3. SEO design

**Single-facet (canonical, indexable):**
- TYPE: `/investors/<angel|vc-firm|micro-vc|family-office|accelerator|corporate-vc>`; `/firms/<vc-firm|accelerator>` (OrgType)
- STAGE: `/investors/<pre-seed|seed|series-a|series-b|growth|series-d-plus>`
- SECTOR: `/investors/<fintech|climate|healthcare|ai>` (needs `Industry.slug`)
- GEO: `/investors/<london|united-states|berlin|europe>` (`Geography.slug`)

**Cross-products (curated whitelist, registry-gated ≥N):** TYPE×STAGE (`/investors/angel/pre-seed`), TYPE×SECTOR (`/investors/vc-firm/climate`), STAGE×GEO (`/investors/seed/london`), SECTOR×GEO (`/investors/fintech/london` — highest intent). Pick `/investors/<sector>/<geo>` as canonical; 301 the vanity `/<sector>-investors/<geo>` form.

**Canonical/noindex policy:**
- Index,follow + self-canonical: entity pages, `/investors`, `/firms`, all single-facet, whitelisted ≥N cross-products.
- `noindex,follow` + canonical→browse root: any URL with GET params, 3+ facet combos, below-threshold combos, `page>1`.
- Entity pages self-canonical to absolute https URL (replace hardcoded `og:url=globalify.org/`).

**Sitemap segmentation:** `<sitemapindex>` → `sitemap-investors-N.xml`/`sitemap-firms-N.xml` (50k chunks, `is_public AND is_approved`, lastmod from `updated_at`) + `sitemap-facets.xml` (registry `is_canonical`).

**robots.txt:** `Disallow: /admin /settings /login /claim /payment` + `Disallow: /*?*`; drop OAuth disallows; `Sitemap: https://globalify.org/sitemap.xml`.

**JSON-LD per page:** Person (jobTitle from Affiliation.title, worksFor→Org, sameAs linkedin/twitter/website, address from Geography) on `/investors/<slug>`; Organization (url, sameAs, address, employee from Affiliations) on `/firms/<slug>`; BreadcrumbList everywhere; ItemList on all browse/facet/search pages.

---

## 4. Admin rework + catalog drop

**Rewire (writes BEFORE drop):** admin/settings CRUD moves onto `Person`/`Organization`/`Affiliation`/`InvestorProfile`/`EntityIndustry/Stage/Geography/Notable`; replace removed `upsert_data()/delete_data()` with a per-entity `entity_search.sync_one(type,id)` (the AttributeError root cause). Retire `InvestorBackup` (undo) + `InvestorOriginPoint` (restore) + dedup/merge entirely. `edit_claim_request` → `Person.user_id` via `ClaimRequest.(entity_type,entity_id)`. List views → `Person.get_all`/`Organization`. Fix the `rounds=notable_investments` key bug in `create_investment_firm`.

**Final drop (Alembic `down_revision='c3d4e5f6a7b8'`), FK-safe order:**
1. `claim_request.investor_id` + `claim_verification.investor_id` FK cols
2. `investor_bookmark`, `investment_firm_bookmark`, `investor_backup`, `investor_origin_point`
3. 6 M2M: `investor_{industry,round,notable_investment}`, `investment_firm_{industry,round,notable_investment}`
4. `investor`, `investment_firm`
5. `country` (after `search.py` repoint to `Geography`/`InvestmentStage`)

**Import sites to clear:** `models/__init__.py __all__`, `models/user.py` relationships, `models/claim.py`, `models/backfill.py`, `__init__.py setup` CLI, `routes/main.py`, `routes/search.py`, `routes/settings.py`, `schemas/investor.py`, `admin/investor.py`, `admin/investment_firm.py`. **Keep** `NotableInvestment` (relocate out of `investor.py`), `Industry`, `Round` (lookups feeding `entity_*`). Boot smoke test surfaces any missed import.

---

## 5. Frontend tech decision

- **htmx (primary), self-hosted, not CDN.** All interactive needs (bookmark toggle, filter form, pagination, claim/magic-link send) are server round-trips — `hx-get`/`hx-post` + partial swaps fit and keep logic server-side, preserving crawlability. **Alpine only** for purely-client UI (mobile menu, filter-chip pre-submit) — and prefer dropping it in favor of the existing 7-line `menu.js`. **Do not reintroduce Vue.**
- **Tailwind: stay on v3.4** (config + `postcss.config.js` already correct) — avoid v4 churn this phase. **Build is currently broken**: `node_modules` absent. Fix = `npm install`, then regenerate `main.css` (committed file is stale Feb-2025). Prune dead `view-eric/jennifer/arstan` classes + dead animations. **Content glob must stay `./src/project/templates/**/*.{html,htm}`** so new `profiles/`, `browse/`, `partials/` templates are scanned and classes aren't purged.
- **Asset includes in base:** `<link main.css>`, preload Poppins woff2, self-hosted `htmx.min.js` (defer), PostHog behind config flag. Delete dead `static/elements/*` (SuperConnect, waitlist, hub/academy, Team/, OAuth logos, 1MB `countries.svg`).
- **Progressive-enhancement filters:** plain `<form method=get>` (works JS-off) over existing `search.py` GET params; htmx layer adds `hx-get` + `hx-target=#results` + `hx-push-url=true`; one Jinja partial serves full page and fragment via `HX-Request` header detection.

---

## 6. Risks & verification

**Highest-risk steps:** (1) 2d catalog drop — FK ordering + the `backfill`/`populate_*` old-ORM dependency; do writes first, gate the drop on prod data migration. (2) 2b profile N+1 / discriminator-based `InvestorProfile` fetch with no ORM relationship. (3) 2c facet URL explosion — registry must quality-gate. (4) Tailwind purge dropping classes from new templates if glob/regeneration skipped.

**Playwright verification plan:**
- **Pages:** `/`, `/investors?round=seed` (filter SSR), `/investors/<slug>`, `/investors/seed/fintech`, `/firms/<slug>`, `/firms`.
- **SSR content:** `browser_navigate` + `browser_snapshot` assert key entity text present; second pass with JS disabled confirms content in initial HTML (not hydrated).
- **SEO tags:** `browser_evaluate` checks `document.title`, `meta[name=description]`, `link[rel=canonical]`, `og:title/og:image`, and `JSON.parse(script[type="application/ld+json"])` with expected `@type` (Person/Organization/ItemList/BreadcrumbList).
- **No console errors:** `browser_console_messages` = zero error-level (catches orphaned-Vue / missing-runtime regressions).
- **Progressive enhancement:** filter `<form>` GET updates URL params; `browser_network_requests` shows `HX-Request` + `#results` swap.
- **Pro gating:** assert locked contact info absent from DOM for anonymous users.
- **Catalog drop:** `flask db upgrade` + boot + `ruff` + `pytest` green.

---

## 7. Recommended first sub-plan: **2a (Foundation)**

Start with **2a — CSS build + base layout + SSR partials**. Rationale:
1. **Unblocks all visual verification** — the Tailwind build is broken (`node_modules` absent, stale `main.css`); nothing can be Playwright-verified meaningfully until `npm run css` works.
2. **Every later sub-plan extends `base.html`** and the JSON-LD partials — building 2b profiles or 2c facets first would mean throwaway per-page heads, re-incurring the ~11-head duplication the spec explicitly targets.
3. **Lowest risk, immediately shippable** — reparenting the already-clean salvage set (`index`, `privacy_policy`, `terms_of_service`, errors, `auth/login`) proves the base layout + partial contract end-to-end before touching models, routing, or the high-risk catalog drop.
4. It **centralizes PostHog and `menu.js`**, removing inconsistency before more pages are added.

2a is independent of the broken admin writes and the new-model query layer, so it can ship while 2b's model helpers (`get_by_slug`, `load_profile_bundle`) are being designed in parallel.