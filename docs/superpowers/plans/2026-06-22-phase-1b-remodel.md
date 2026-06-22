# Phase 1b — Data-Model Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Introduce the consolidated **Person / Organization / Affiliation / investor_profile / geography + polymorphic `entity_*` facet** model alongside the existing catalog, build and test a backfill that maps the old `Investor`/`InvestmentFirm` data into it, repoint claims/bookmarks/search-history onto it, and drop the already-dead platform tables — all verified on sqlite. The destructive drop of the *old catalog* tables is deferred to Phase 1c (after search is rewritten onto the new model), to avoid a search-dead window.

**Architecture:** New models are added **additively** (old catalog models stay live so existing search keeps working). A pure `backfill_entities(session)` function does the data mapping and is unit-tested on a seeded in-memory sqlite DB with row-count/spot-check parity assertions. Alembic gets an additive revision (new tables) and a guarded data revision (calls the backfill); the destructive catalog drop is a **separate, gated** revision authored in 1c. Design reference: **`docs/phase-1-planning-brief.md` §3** (target columns, enums, backfill steps, the polymorphic-discriminator decision).

**Tech Stack:** Python 3.14, SQLAlchemy 2.0 (typed `Mapped`), Alembic (Flask-Migrate), pytest, sqlite (tests) / Postgres (prod).

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never `main`.
- **Discriminator convention (brief §3):** all polymorphic refs use a `(entity_type ENUM('person','org'), entity_id INT)` pair — matching the Typesense `f"{entity_type}_{db_id}"` id scheme. No shared surrogate `entity` table; integrity enforced in the app layer (document it). Use a single `EntityType` enum.
- **Additive only in 1b:** do NOT drop the `investor`/`investment_firm` tables or their models, and do NOT touch `sync_search_index`/`get_search`/`SearchBuilder` (Phase 1c owns the catalog drop + search rewrite). 1b MAY drop the already-dead platform tables (`company`, `user_company`, `company_invitation`, `company_bookmark`, `investment`, `funding_round`) and the dead `user`/`user_info` columns, since nothing in the ORM references them after Phase 1a.
- **Prod migration is GATED:** the destructive Alembic revision must run only against a backed-up DB. Build + test everything on sqlite; do NOT attempt to run migrations against any real Postgres in this plan. Each task's gate is sqlite-based.
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run python -c "import sys; sys.path.insert(0,'src'); import project"` exits 0; `uv run pytest` green (incl. `test_db_metadata_creates_all_tables`); `uv run ruff check . && uv run ruff format --check .` clean.
- **Commits:** conventional subject; end with `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: New ORM models + enums (additive)

Add the new model layer in a focused new module, registered so `db.create_all()` builds the tables. Old models untouched.

**Files:**
- Create `src/project/models/entity.py` — `Person`, `Organization`, `Affiliation`, `InvestorProfile`, `Geography`, `EntityIndustry`, `EntityStage`, `EntityGeography`, `EntityNotable`, `EntityBookmark`.
- Modify `src/project/utils/enums.py` — add `EntityType`, `OrgType`, `PersonType`, `AffiliationRole`, `InvestorType`, `InvestmentStage`, `LeadPreference`.
- Modify `src/project/models/__init__.py` — export the new models.
- Create `tests/test_entity_models.py`.

**Interfaces (produced — later tasks rely on these exact names/types):**
- `EntityType(StrEnum)`: `PERSON = "person"`, `ORG = "org"`.
- `Person`: `id:int pk`, `first_name:str`, `last_name:str|None`, `slug:str unique`, `about:str|None`, `headline:str|None`, `website/linkedin/twitter/email/phone_number:str|None`, `is_public:bool=False`, `is_approved:bool=False`, `user_id:int|None FK user.id`, `search_index:str|None`, `created_at:datetime`.
- `Organization`: `id`, `name:str`, `slug:str unique`, `about/website/linkedin/twitter/email/phone_number:str|None`, `n_employees:int|None`, `org_type:OrgType`, `is_public:bool=True`, `is_approved:bool=False`, `search_index:str|None`, `created_at`.
- `Affiliation`: `id`, `person_id FK person.id`, `organization_id FK organization.id`, `title:str|None`, `role:AffiliationRole`, `is_current:bool=True`, `UniqueConstraint(person_id, organization_id, role)`.
- `InvestorProfile`: `id`, `entity_type:EntityType`, `entity_id:int`, `investor_type:InvestorType|None`, `min_investment:int|None (BigInteger)`, `max_investment:int|None`, `n_investments:int|None`, `n_exits:int|None`, `thesis:str|None (Text)`, `lead_pref:LeadPreference|None`, `accepts_cold_inbound:bool=False`, `is_active:bool=True`, `UniqueConstraint(entity_type, entity_id)`.
- `Geography`: `id`, `slug:str unique`, `name:str`, `type:str` (country|region|city), `country_code:str|None`, `latitude/longitude:float|None`.
- `EntityIndustry`/`EntityStage`/`EntityGeography`/`EntityNotable`: each `id`, `entity_type:EntityType`, `entity_id:int`, plus respectively `industry_id FK industry.id`, `stage:InvestmentStage`, `geography_id FK geography.id`, `notable_investment_id FK notable_investment.id`. Add a `UniqueConstraint(entity_type, entity_id, <facet>)` on each.
- `EntityBookmark`: `id`, `user_id FK user.id`, `entity_type:EntityType`, `entity_id:int`, `created_at`, `UniqueConstraint(user_id, entity_type, entity_id)`; staticmethods `get_by_user_id(user_id)`, `exists(user_id, entity_type, entity_id)`.
- Enum members: `OrgType`: vc_firm, micro_vc, angel_group, corporate_vc, family_office, accelerator, incubator, venture_studio, pe_firm, growth_equity, syndicate, lp_fund_of_funds, grant_program, government_program, venture_debt, crowdfunding_platform, search_fund, hedge_fund, other. `PersonType`: angel, partner, operator, scout, lp. `AffiliationRole`: founder, gp, partner, principal, associate, scout, advisor, lp, operator. `InvestorType`: (union per brief §3 field-set). `InvestmentStage`: idea, pre_seed, seed, series_a, series_b, series_c, series_d_plus, growth, late_stage, debt, secondary. `LeadPreference`: lead, follow, both, unknown.

- [ ] **Step 1: Read `docs/phase-1-planning-brief.md` §3** and the current `models/investor.py` column types (to match `Mapped`/types/`MappedAsDataclass` conventions used in the repo).
- [ ] **Step 2: Add the enums** to `utils/enums.py` (follow the existing `StrEnum` style).
- [ ] **Step 3: Write `tests/test_entity_models.py` first** — a test that, under the `app` fixture + `db.create_all()`, creates a `Person`, an `Organization`, an `Affiliation` linking them, an `InvestorProfile` for each, and one of each `entity_*` facet + an `EntityBookmark`, commits, and reads them back asserting the relationships/uniqueness. Run it; it fails (no `entity` module).
- [ ] **Step 4: Implement `src/project/models/entity.py`** per the interfaces above (match the repo's `MappedAsDataclass`/`Mapped[...]`/`mapped_column` style; relationships declared with `init=False`).
- [ ] **Step 5: Export the new models** from `models/__init__.py`.
- [ ] **Step 6: Run the gate** + the new tests (the existing `test_db_metadata_creates_all_tables` must still pass — new tables create cleanly alongside old).
- [ ] **Step 7: Commit** (`feat(model): add Person/Org/Affiliation/InvestorProfile/Geography/entity_* models`).

---

## Task 2: Backfill function + parity tests

A pure function that maps the old catalog into the new model, fully tested on a seeded sqlite DB.

**Files:**
- Create `src/project/models/backfill.py` — `def backfill_entities(session) -> dict` (returns a counts report).
- Create `tests/test_backfill.py`.

**Interfaces (consumed):** the Task 1 models; the existing `Investor`, `InvestmentFirm`, `NotableInvestment`, `Industry`, `Round`, `InvestorBookmark`, `InvestmentFirmBookmark`, `SearchHistory` models and their columns.

**Backfill mapping (brief §3 "Data backfill steps"):**
- Each `Investor` → one `Person` (map first_name/last_name/slug/about/position→headline/website/linkedin/twitter/email/phone_number/is_public/is_approved/user_id/search_index).
- Each `InvestmentFirm` → one `Organization` (map name/slug/about/website/linkedin/twitter/email/phone_number/n_employees; default `org_type=OrgType.vc_firm`, `is_public=True`).
- Each `Investor.firm_name` (non-empty) → match against `Organization.name` (exact, then `thefuzz` ratio ≥ 90); on match create `Affiliation(person, org, role=AffiliationRole.partner)`; on no match create a stub `Organization(name=firm_name, org_type=other)` then the affiliation. Report stub count.
- One `InvestorProfile` per person and per org from `min_investment/max_investment/n_investments/n_exits` (+ `about`→`thesis` for orgs where useful). `accepts_cold_inbound=False`, `is_active=True`.
- `Investor.industries`/`InvestmentFirm.industries` M2M → `EntityIndustry` rows (entity_type per source). Same for rounds → `EntityStage` (map `Round.name` → `InvestmentStage`; expand `Series B+`→ series_b & series_c per the old populate logic) and notable investments → `EntityNotable`.
- `Investor.location`/`InvestmentFirm.location` → look up or create a `Geography` (type=city, derive slug); link via `EntityGeography`. Drop coordinates.
- `InvestorBookmark` rows → `EntityBookmark(entity_type=person)`; `InvestmentFirmBookmark` → `EntityBookmark(entity_type=org)`.
- Do NOT migrate `InvestorBackup`/`InvestorOriginPoint` rows (dropped).

- [ ] **Step 1: Write `tests/test_backfill.py` first** — under the `app` fixture: `db.create_all()`, seed a small fixture (2 Investors — one with a `firm_name` matching a seeded InvestmentFirm, one with an unmatched firm_name; 1 InvestmentFirm; a couple industries/rounds/notable + a bookmark), run `backfill_entities(db.session)`, then assert: `Person` count == Investor count; `Organization` count == InvestmentFirm count + stub count; the matched affiliation links to the right org; the unmatched firm_name created a stub org + affiliation; `InvestorProfile` exists per entity; `EntityIndustry`/`EntityStage` counts match the seeded M2M; `EntityBookmark` count == sum of old bookmarks. Run it; it fails (no `backfill` module).
- [ ] **Step 2: Implement `backfill_entities`** per the mapping. Make it idempotent-safe to re-run is NOT required, but it must not duplicate within a single run.
- [ ] **Step 3: Run the new tests + full gate.**
- [ ] **Step 4: Commit** (`feat(model): add backfill_entities mapping old catalog → new entity model`).

---

## Task 3: Repoint claims, search-history & bookmark API to the new model

Move the user-facing references off the old `investor_id` FKs onto the polymorphic entity ref, so dropping the old catalog later (1c) doesn't break them.

**Files:** modify `models/claim.py` (`ClaimRequest`, `ClaimVerification` — add `entity_type`/`entity_id`, keep old `investor_id` nullable for the migration window; update their query helpers `get_all`/`get_pending_by_user_id` which use raw table literals), `models/search.py` (`SearchHistory.type` remap `investor`→person/`investment_firm`→org; the `SearchHistoryType` enum), and the bookmark call sites in `routes/settings.py`/`routes/main.py` to use `EntityBookmark`. Add `tests/test_claim_repoint.py`.

- [ ] **Step 1: Write a test** that a `ClaimVerification`/`ClaimRequest` can be created against `(entity_type=person, entity_id=...)` and queried back; that `EntityBookmark` add/exists/list works from the settings bookmark handler path. Run; fails.
- [ ] **Step 2: Add `entity_type`/`entity_id` to the claim models** (nullable `investor_id` retained for now); fix the raw-SQL query helpers to use the ORM/new columns.
- [ ] **Step 3: Repoint the surviving bookmark handlers** in `settings.py`/`main.py` to `EntityBookmark`.
- [ ] **Step 4: Run the gate + tests.**
- [ ] **Step 5: Commit** (`refactor(model): repoint claims/search-history/bookmarks to polymorphic entity ref`).

---

## Task 4: Alembic migrations (additive + backfill) + drop dead platform tables

Author the Alembic revisions for prod. Verify the additive + backfill path on a scratch sqlite DB; the catalog-drop is deferred to 1c.

**Files:** create migration revisions under `migrations/versions/`. Modify nothing else.

- [ ] **Step 1: Generate the additive revision** — `uv run flask db revision -m "add entity model"` then hand-edit to `op.create_table(...)` for all Task 1 tables + enums (don't trust autogenerate blindly; review against the models). Include geography seed if trivial, else leave for the seeder.
- [ ] **Step 2: Add a data-migration revision** that imports and calls `backfill_entities` within `op.get_bind()` session context (guarded so it no-ops on an empty DB).
- [ ] **Step 3: Add a "drop dead platform tables" revision** — drop `company`, `user_company`, `company_invitation`, `company_bookmark`, `investment`, `funding_round`, `country`, and the dead `user.oauth_provider`/`user.is_investor_mode_active`/`user_info.refuse_all_invitations` columns. Respect FK order. (Do NOT drop `investor`/`investment_firm` — that's 1c.) Provide `downgrade()` where feasible; mark the data revision one-way.
- [ ] **Step 4: Verify on scratch sqlite** — point `_DATABASE_URL` at a temp sqlite file, `uv run flask db upgrade`, confirm it reaches head without error on an empty DB; then `flask db downgrade` the additive revision. Document that the data + drop revisions are validated structurally here and must run against a **backed-up Postgres snapshot** in prod (gated).
- [ ] **Step 5: Run the full gate** (pytest still green).
- [ ] **Step 6: Commit** (`feat(migration): additive entity tables + backfill + drop dead platform tables`).

---

## Self-Review

**Coverage (brief §3, the additive/non-catalog-drop subset):** new models + enums (T1) · backfill mapping (T2) · claim/search/bookmark repoint (T3) · Alembic additive+backfill+dead-table-drop (T4). 

**Deferred to 1c (intentional, not gaps):** dropping `investor`/`investment_firm` tables + models; rewriting `get_search`/`sync_search_index` onto the unified entity; single Typesense collection + Gemini. **Deferred to prod (gated):** running the data + drop revisions against real Postgres (needs a backup/snapshot).

**Risk control:** old catalog stays live so search keeps working through 1b; backfill is a pure, unit-tested function; destructive prod steps are isolated in their own Alembic revision and never executed in this plan.
