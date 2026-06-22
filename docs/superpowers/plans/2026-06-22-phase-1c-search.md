# Phase 1c — Typesense v30 + Single Collection + Search Rewrite

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Upgrade to the Typesense 2.x client / v30 server, collapse the per-type collections into one `entities` collection over the new Person/Org model, rewrite `get_search`/`sync_search_index`/`SearchBuilder` onto it (fixing the country-filter, `delete_data`, and swallow-all-exceptions bugs), make the embedder configurable (local MiniLM for dev/test, Gemini for prod), flip the search routes, and then drop the old catalog tables.

**Architecture:** New search code targets one `entities` collection keyed `id = f"{entity_type}_{db_id}"` with an `entity_type` facet. Built and tested against a **Dockerized Typesense v30** using the built-in `ts/all-MiniLM-L12-v2` embedder (zero external key); the embedder is env-configurable so prod uses Gemini (`GEMINI_API_KEY`). The old catalog stays live until the search flip lands, then a final gated Alembic revision drops it. Design reference: **`docs/phase-1-planning-brief.md` §4**.

**Tech Stack:** Typesense v30 (Docker) + `typesense` 2.x client, SQLAlchemy, pytest. Gemini embeddings (prod, gated on `GEMINI_API_KEY`).

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never `main`.
- **Embedder is configurable, default-safe:** a setting (e.g. `settings.typesense_embedder`) selects `minilm` (built-in `ts/all-MiniLM-L12-v2`, no key — the dev/test/CI default) vs `gemini` (remote `model_config={model_name: "google/text-embedding-004", api_key: <GEMINI_API_KEY>}`). Code must build the collection schema for either; live Gemini is gated on the key being present.
- **Test against real Typesense v30 in Docker**, not mocks, for the sync/search tasks. Spin up `typesense/typesense:30.2` (or latest 30.x) on a throwaway port with an `xyz` api key; tear it down after. Tests that require Typesense must skip cleanly (pytest skip) when no Typesense is reachable, so CI (no Typesense) stays green — but the implementer MUST run them against Docker locally and report results.
- **Bug fixes to land (brief §4):** `country` filter → `country_code`/`geographies` (the old `countries` vs `country` mismatch); `delete_data` filters by **both** `db_id` AND `entity_type`; remove the broad `except Exception` swallow (log/raise in non-prod); fix the `InvestmentFirm.sync_search_index` duplicate-key (`min_investment` written twice) when porting.
- **Ordering:** the destructive catalog drop (Task 4) runs ONLY after the search routes are flipped onto the new collection (Task 3). Prod migration gated on a DB backup.
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run pytest` green; `uv run ruff check . && uv run ruff format --check .` clean; app imports.
- **Commits:** conventional subject; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: Bump to Typesense 2.x client + adapt `typesense_search.py`

**Files:** `pyproject.toml`/`uv.lock` (unpin typesense, move to `>=2.0`), `src/project/utils/typesense_helpers/typesense_search.py`.

- [ ] **Step 1:** `uv remove typesense && uv add "typesense>=2.0"` (or edit the pin to `>=2.0,<3`), `uv sync`.
- [ ] **Step 2:** Adapt the module-level `Client` init and `SearchBuilder` to the 2.x API. Verify import paths (`typesense.client.Client`, `typesense.exceptions.ObjectNotFound`). Update `documents.import_` result handling for the 2.x return shape. Replace collection-scoped synonyms with a `create_synonym_sets()` using the global `client.synonym_sets.upsert(...)` (v30). Keep `SearchBuilder`'s fluent API surface (callers in Task 2 rely on it).
- [ ] **Step 3 (Docker smoke):** start `docker run -d --name ts-test -p 18108:8108 typesense/typesense:30.2 --data-dir /data --api-key=xyz --enable-cors` (create a tmp data dir or use a volume); wait for `/health`; with `_TYPESENSE_HOST=localhost _TYPESENSE_PORT=18108 _TYPESENSE_API_KEY=xyz`, run a throwaway script: create a tiny collection, index a doc, search it, assert a hit. Tear down `docker rm -f ts-test`.
- [ ] **Step 4: Gate** (pytest still green — Typesense-dependent code is not exercised by the sqlite tests) + ruff.
- [ ] **Step 5: Commit** (`build: bump typesense client to 2.x and adapt SearchBuilder/synonyms for v30`).

---

## Task 2: Single `entities` collection — `Entity.sync_search_index` + `Entity.get_search`

**Files:** create `src/project/models/entity_search.py` (or add to `entity.py`) with the schema + sync + search; `tests/test_entity_search.py`.

Build per **brief §4 "Single `entities` collection schema"** and "get_search / SearchBuilder / sync rewrite outline":
- Schema fields: `id`, `entity_type` (facet), `db_id` (facet), `name`, `slug`, `about`, `headline/position`, `org_name` (person's affiliated org), `person_names[]` (org's partners), socials, `country_code` (facet), `geographies[]` (facet), `industries[]` (facet), `stages[]` (facet), `notable_investments[]`, `investor_type` (facet), `lead_pref` (facet), `accepts_cold_inbound` (facet), `is_active` (facet), `check_size_min/max` (sort), `n_investments/n_exits` (sort), `embedding` (configurable embedder).
- `Entity.sync_search_index(recreate=False)`: iterate Person + Organization batches, build the doc per entity (join affiliations, investor_profile, entity_* facets, geography), upsert; write `search_index = f"{entity_type}_{db_id}"` back to the row. ONE method (not two). Configurable embedder.
- `Entity.get_search(entity_type=None, query, filters..., page)`: build the Typesense query via `SearchBuilder`; filter on `country_code`/`geographies` (NOT `countries`); hybrid (include `embedding` in `query_by`); decay/recency optional. Do NOT swallow all exceptions — log + re-raise in non-prod.
- `delete_data(entity_type, db_id)`: filter by both fields.

- [ ] **Step 1:** Write `tests/test_entity_search.py` — Typesense-v30-Docker-gated (skip if unreachable): backfill a few Person/Org rows (reuse the backfill or seed directly), `Entity.sync_search_index(recreate=True)`, then assert: a keyword query returns the expected entity; an `entity_type=person` filter returns only persons; a `country_code` filter returns the right docs (regression for the old zero-match bug); `delete_data(person, id)` removes only that doc (not an org with the same db_id).
- [ ] **Step 2:** Implement the schema + sync + search + delete against MiniLM.
- [ ] **Step 3 (Docker):** run the new tests against Dockerized Typesense v30; report results. Gate (sqlite tests still green) + ruff.
- [ ] **Step 4: Commit** (`feat(search): single entities collection with Entity.sync_search_index + get_search`).

---

## Task 3: Flip search routes + reindex CLI; remove old search code

**Files:** `src/project/routes/search.py` (use `Entity.get_search` + `Geography`, drop `Country`/investor-mode remnants), `src/project/models/investor.py` + `user.py` (remove the old `get_search`/`sync_search_index`/`upsert_data`/`delete_data` — the catalog model columns stay until Task 4), `src/project/__init__.py` (rewrite the `setup` CLI to seed + `Entity.sync_search_index`; add a non-destructive `reindex` CLI command that runs `Entity.sync_search_index(recreate=False)` WITHOUT `db.drop_all`).

- [ ] **Step 1:** Repoint `search.py` handlers to `Entity.get_search`; replace `Country.get_all()` facet sources with `Geography`. Keep the routes returning data the (Phase-2-rebuilt) templates can consume; don't perfect templates.
- [ ] **Step 2:** Remove the old `get_search`/`sync_search_index` from `investor.py`/`user.py`; update the `setup` CLI to call `Entity.sync_search_index`; add `flask reindex` (non-destructive).
- [ ] **Step 3:** Gate (pytest green — update `test_no_url_for_to_unregistered_endpoints` stays green; the search routes still register) + ruff. Spot-check `flask setup`/`reindex` against a scratch sqlite + Docker Typesense if feasible.
- [ ] **Step 4: Commit** (`refactor(search): flip routes to entities collection, add non-destructive reindex CLI`).

---

## Task 4: Drop the old catalog (gated destructive migration)

**Files:** new Alembic revision under `migrations/versions/`; `src/project/models/investor.py` (remove the old `Investor`/`InvestmentFirm`/`NotableInvestment`-as-old-shape models + `InvestorBackup`/`InvestorOriginPoint`/old bookmarks), `models/__init__.py`, `models/helpers.py` (remove `Country`).

- [ ] **Step 1:** New Alembic revision: drop `investor`, `investment_firm`, their ~9 M2M tables, `investor_backup`/`investor_origin_point` (+ their M2M), `investor_bookmark`, `investment_firm_bookmark`, and `country` (deferred from 1b). FK-safe order. Drop the old `claim.investor_id` column (claims now use entity ref). One-way; document.
- [ ] **Step 2:** Remove the corresponding ORM models; keep `NotableInvestment` only if still referenced by `entity_notable` (it is — keep it, already de-companied).
- [ ] **Step 3 (Docker PG):** verify the full migration chain reaches head on Postgres 16 (after `create_all`+stamp per the known pre-existing base-chain quirk, or from the 1b head). Confirm `db.create_all()` + `test_db_metadata_creates_all_tables` still pass (no model references a dropped table).
- [ ] **Step 4:** Gate (pytest green) + ruff. **Prod run gated on a DB backup.**
- [ ] **Step 5: Commit** (`feat(migration): drop old catalog tables; remove legacy investor/firm models`).

---

## Self-Review

**Coverage (brief §4):** client 2.x + v30 synonym_sets (T1) · single `entities` collection + sync + search + bug fixes (T2) · route flip + reindex CLI + remove old search (T3) · drop old catalog (T4). 

**Gated/deferred:** live Gemini embeddings (needs `GEMINI_API_KEY` — built configurable, MiniLM-tested); prod migration run (needs DB backup). **Carried to 1d:** orphaned schema files, mislabeled admin stubs, the `[tool.uv].dev-dependencies` deprecation, `headline` vs `position` naming, `SearchHistoryType` legacy members.

**Risk control:** old catalog/search stays live through T1–T2; routes flip in T3; only then T4 drops the old tables. Every search task verified against real Typesense v30 in Docker.
