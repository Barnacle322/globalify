# Phase 2d — Admin Rewire + Catalog Retirement

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Rewire the admin/settings CRUD onto the new Person/Organization/entity model (with per-entity reindex), decouple the seed path from the old models, then delete the vestigial `Investor`/`InvestmentFirm` ORM models and drop their tables — completing the data-model consolidation that's been deferred since Phase 1c.

**Architecture:** Add `entity_search.sync_one(entity_type, id)` so admin edits re-index a single entity. Rewire admin/settings writes onto `Person`/`Organization`/`Affiliation`/`InvestorProfile`/`entity_*`. Replace the CSV→old-model→`backfill_entities`→sync seed chain with a direct new-model demo seeder (the full legacy CSV is superseded by the Phase 6 collectors). Only then can the old models be deleted and their tables dropped (a separate, prod-gated Alembic revision verified on Docker Postgres). Design reference: **`docs/phase-2-planning-brief.md` §4** (rewire list + FK-safe drop order + import sites).

**Tech Stack:** Flask, SQLAlchemy, Alembic, Typesense v30, Docker (Postgres + Typesense verification).

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never `main`.
- **Writes before drop:** admin/settings must be rewired (and the seed path decoupled) BEFORE the old models/tables are deleted — at no commit may the app fail to import.
- **The destructive Alembic revision is PROD-GATED:** verify it on Docker Postgres; do NOT run it against any real DB in this plan.
- **`NotableInvestment`, `Industry`, `Round` stay** (they feed `entity_notable`/`entity_industry`/stages) — only relocate `NotableInvestment` out of `investor.py` so deleting that file is clean.
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run pytest` green; `uv run ruff check . && uv run ruff format --check .` clean; app imports + `db.create_all()` (the `test_db_metadata_creates_all_tables` test). Docker where stated.
- **Commits:** conventional subject; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: `sync_one` + relocate `NotableInvestment`

**Files:** `src/project/models/entity_search.py` (add `sync_one`), relocate `NotableInvestment` from `models/investor.py` → `models/entity.py` (or `helpers.py`) and repoint imports (`entity_search.py`, `models/__init__.py`, anywhere using it), `tests/`.

- [ ] **Step 1:** Add `sync_one(entity_type: EntityType, entity_id: int)` to `entity_search.py` — builds the single entity doc (reuse the per-entity doc-building from `sync_search_index`) and upserts it; and a delete path. Refactor `sync_search_index` to call the shared doc-builder so there's one source of truth.
- [ ] **Step 2:** Move the `NotableInvestment` class out of `investor.py` into `entity.py` (it's referenced by `entity_notable`/`EntityNotable`); update every import site. `Investor`/`InvestmentFirm` stay in `investor.py` for now.
- [ ] **Step 3:** Test (sqlite): `sync_one` builds the right doc shape for a Person and an Org (unit-test the doc-builder without Typesense, or Docker-gate a real upsert). `NotableInvestment` still creates + relates.
- [ ] **Step 4: Gate. Commit** (`feat(search): add sync_one per-entity reindex; relocate NotableInvestment to entity.py`).

---

## Task 2: Rewire admin + settings onto the new model

**Files:** `src/project/routes/admin/investor.py`, `admin/investment_firm.py`, `admin/__init__.py` (`edit_claim_request`), `routes/settings.py` (investor management), and the templates they render (minimal — reshape data, don't rebuild UI).

- [ ] **Step 1:** `admin/investor.py`: rewrite create/update/approve/delete + list/search to operate on `Person` (+ `Affiliation`/`InvestorProfile`/`EntityIndustry/Stage/Geography/Notable`); call `entity_search.sync_one(PERSON, id)` on save and the delete path on delete. **Delete** `undo_investor_data`/`restore_investor_data`/`duplicates`/`merge_investors` (backup/restore/dedup retired). Remove the stale `upsert_data`/`delete_data` try/except stubs.
- [ ] **Step 2:** `admin/investment_firm.py`: same onto `Organization` (+ `InvestorProfile`/`entity_*`); fix the latent `rounds=...notable_investments` key bug; `sync_one(ORG, id)`.
- [ ] **Step 3:** `admin/__init__.edit_claim_request` → resolve the claim's target via `ClaimRequest.(entity_type, entity_id)` → set `Person.user_id`. `settings.py` `index`/`edit_investor`/`investor_list_view`/`investment_firms_list_view` → `Person`/`Organization`; **delete** `investor_point_origin_data`/`restore_investor_data` + the `InvestorOriginPointSchema` usage.
- [ ] **Step 4:** Templates these render: reshape the passed context to the new model fields (keep the admin UI functional; don't redesign). If a template references a removed field, fix minimally.
- [ ] **Step 5: Gate** (pytest green; ruff; import). The admin write paths aren't unit-tested — Docker-verify a create/update reflects in search in Task 5's pass, or smoke an admin create here if feasible.
- [ ] **Step 6: Commit** (`refactor(admin): rewire investor/firm/claim CRUD onto Person/Org/entity model + sync_one`).

---

## Task 3: Direct new-model seeder; retire `backfill` + old CSV seeders from the live path

**Files:** `src/project/__init__.py` (`setup` CLI), a new `src/project/models/seed.py` (`seed_demo_entities`), retire `models/backfill.py`'s use in `setup` (keep the function only if a migration still references it — the Phase 1b data revision does; leave `backfill.py` but stop using it in `setup`).

- [ ] **Step 1:** Write `seed_demo_entities(session)` creating ~25 diverse demo entities directly in the NEW model: a mix of `Person` (angels/partners) + `Organization` (vc_firm/micro_vc/accelerator/family_office/pe_firm...) with `slug`, `is_public=True`, `is_approved=True`, an `InvestorProfile` (check sizes, investor_type, stages via `EntityStage`, lead_pref, accepts_cold_inbound), `EntityIndustry` (sector slugs), `EntityGeography` (geo), and some `Affiliation`s — spread across types/stages/sectors/geos so facet pages have data. Plus the 2 hardcoded admin users.
- [ ] **Step 2:** Rewrite the `setup` CLI: `db.drop_all()` + `create_all()` → seed admins → `seed_demo_entities` → `entity_search.sync_search_index(recreate=True)`. Remove the `Investor.populate_demo`/`InvestmentFirm.populate_vcsheet`/`backfill_entities` calls. (The Phase 1b backfill migration still exists for prod data; `setup` no longer needs the old models.)
- [ ] **Step 3:** Confirm NOTHING in the live import graph (excluding Alembic revision files + `backfill.py` itself) imports `Investor`/`InvestmentFirm` for seeding anymore.
- [ ] **Step 4: Gate** (pytest green; ruff; import; `db.create_all` test). Docker-verify `flask setup` end-to-end against Docker Typesense in Task 5.
- [ ] **Step 5: Commit** (`feat(seed): direct new-model demo seeder; decouple setup from old catalog`).

---

## Task 4: Delete the old ORM models + clear all import sites

**Files:** `models/investor.py` (delete `Investor`/`InvestmentFirm`/`InvestorBookmark`/`InvestmentFirmBookmark`/`InvestorBackup`/`InvestorOriginPoint` + their 6 M2M tables — the file may become empty/deletable), `models/__init__.py` (`__all__`), `models/user.py` (strip `User.investor`/`investor_bookmarks`/`investment_firm_bookmarks`/backup relationships), `models/claim.py` (drop `investor_id` FK col + `relationship("Investor")` + `get_with_investor_by_user_id`/`get_by_investor_id`; keep `entity_type`/`entity_id`), `schemas/investor.py` (delete or replace with new-model schemas), any remaining `routes/search.py`/`main.py` references.

- [ ] **Step 1:** Delete the old model classes + M2M tables; strip the `User`/`claim` relationships/columns to them; update `models/__init__.py`.
- [ ] **Step 2:** Delete/replace `schemas/investor.py`; clear remaining import sites (grep `Investor`/`InvestmentFirm` across `src/` — only `backfill.py` + Alembic revisions may still reference them; everything else must be clean).
- [ ] **Step 3: Gate** — `import project` must succeed (SQLAlchemy mapper-configures cleanly with no dangling relationship), `db.create_all()` works (no FK to a now-unmapped table — note the actual TABLES still exist until Task 5's migration; the MODELS just stop mapping them, which is fine), pytest green, ruff. Grep-clean: no live `src/` code (outside `backfill.py`/migrations) imports `Investor`/`InvestmentFirm`.
- [ ] **Step 4: Commit** (`refactor(model): delete legacy Investor/InvestmentFirm ORM models + clear import sites`).

---

## Task 5: Destructive Alembic drop (prod-gated) + full Docker verification

**Files:** new Alembic revision under `migrations/versions/` (`down_revision` = current head, e.g. the `d1e2f3a4b5c6` Industry.slug rev).

- [ ] **Step 1:** New revision dropping, in FK-safe order: `claim_request.investor_id` + `claim_verification.investor_id` columns → `investor_bookmark`, `investment_firm_bookmark`, `investor_backup`, `investor_origin_point` → the 6 M2M tables → `investor`, `investment_firm` → `country` (deferred from 1b; search no longer uses it). Provide best-effort downgrade or document one-way.
- [ ] **Step 2: Docker Postgres verify (full chain):** `docker run` Postgres 16; run the FULL migration chain to head (per the known base-chain quirk: `db.create_all()` + `flask db stamp <prior-head>` then `flask db upgrade`, OR run from the 1b head) — confirm it reaches head and the old tables are gone (`\dt` shows no `investor`/`investment_firm`/`country`). Tear down.
- [ ] **Step 3: Docker full end-to-end verify:** Postgres + Typesense v30 in Docker; `flask setup` (new seeder → sync); run the app; Playwright: `/investors` (browse shows seeded), a `/investors/<slug>` (profile), `/investors/seed` (facet), and an admin create/update reflecting in search (`sync_one`). 0 console errors. Tear down both containers.
- [ ] **Step 4: Gate** (pytest green; ruff; import). **Prod migration gated on a DB backup.**
- [ ] **Step 5: Commit** (`feat(migration): drop legacy catalog tables (investor/investment_firm/country/M2M/backups)`).

---

## Self-Review

**Coverage (brief §4):** sync_one + NotableInvestment relocate (T1) · admin/settings rewire (T2) · seed decouple (T3) · delete old models + import sites (T4) · destructive Alembic drop + Docker verify (T5). 

**Deferred/carried:** the `/search`→`/investors` + `/search/investment-firms`→`/firms` 301s (now possible once legacy search routes are retired in T2/T4 — fold in if clean, else carry to 2e); `backfill.py` stays (the Phase 1b data migration references it) but is no longer used by `setup`; prod migration run (gated on backup).

**Risk control:** strict ordering (rewire + seed-decouple before delete; delete models before dropping tables); each commit keeps the app importable + `db.create_all` green; the destructive migration is isolated + Docker-verified, never run on prod here. After 2d the old data model is fully gone and the entity model is the sole catalog.
