I'll write the planning brief directly. This is a synthesis task using the provided scoping data — no codebase exploration is needed since the scoping data already cites exact symbols, line numbers, and file paths.

# Globalify Phase 1 Planning Brief — Strip + Remodel

## 1. Sub-plan decomposition

Phase 1 is decomposed into four ordered, independently-shippable sub-plans. The driving constraint: **dangling references break imports at module load**, so deletions and repoints must be sequenced so that at no commit boundary does a kept module import a deleted symbol, and the destructive DB migration runs only once against a code tree that already matches the target ORM.

| Sub-plan | Goal | Risk |
|---|---|---|
| **1a — Strip dead platform** | Delete OAuth, Stripe, GCS, Pub/Sub, reCAPTCHA, googlemaps, the Vue SPA, companies/onboarding/funding/investment/payment/profile routes+templates, and all entrepreneur-matching/suggestion code. Leave a compiling tree with the *old* catalog model still intact. | Medium |
| **1b — Data-model consolidation + Alembic migration** | Introduce `person`/`organization`/`affiliation`/`investor_profile`/`geography` + polymorphic `entity_*` facet joins; backfill from `Investor`/`InvestmentFirm`/`firm_name`/M2M; drop the 12 M2M tables, `InvestorBackup`/`InvestorOriginPoint`, `Investment`/`FundingRound`, `Company`/`UserCompany`/etc. | **High** (destructive, irreversible backfill) |
| **1c — Typesense v30 + single `entities` collection + search rewrite** | Bump client to 2.x, collapse `investors`/`investment_firms`/`companies`/`cities` into one `entities` collection, swap local embedder for Gemini remote, migrate synonyms→synonym_sets, rewrite `SearchBuilder`/`get_search`/`sync_search_index`. | **High** (search cutover; embedder reachability) |
| **1d — Wiring cleanup + CLI + deps + config** | Finalize `pyproject.toml` removals, `cloudbuild.yaml` env pruning, the `flask setup` rewrite, the new non-destructive reindex CLI, and enum pruning. | Low–Medium |

### Ordering justification

- **1a before 1b.** Strip first so the destructive migration does not have to fight live code paths that read deleted columns/tables. Many of the deletions in 1a (e.g. `SuggestionBuilder`, `CompanySuggestionBuilder`, `Investment` route/admin CRUD, `populate_blockchain`, `fix_twitter_links`) reference models that 1b will reshape; removing the readers first means 1b's ORM rewrite touches a smaller surface and no deleted route re-imports a renamed model. Crucially, 1a leaves the **old** `Investor`/`InvestmentFirm`/M2M tables intact, because 1b's backfill reads them.
- **1b before 1c.** Typesense `sync_search_index` reads from the DB. The single-collection sync (`Entity.sync_search_index`) must iterate `person`+`org` rows with `entity_*` eager loads — those tables don't exist until 1b lands. The raw `UPDATE investor SET search_index=...` back-fill SQL (investor.py:1079/1739) must retarget the `person`/`organization` tables, which only exist post-1b.
- **The one remodel-before-strip exception, handled inside 1b.** `ClaimVerification.investor_id` / `ClaimRequest.investor_id` FK→`investor.id`, `User.investor`/`investor_bookmarks`/`investment_firm_bookmarks` back_populates, and `SearchHistoryType` all *repoint* onto the new entity. You cannot drop the `investor` table (a delete) until those FKs/relationships are repointed (a remodel). So within 1b the repoints precede the final `DROP TABLE investor`. This is why claim-FK repointing lives in 1b, not 1a.
- **1d last.** Removing deps from `pyproject.toml` and env vars from `cloudbuild.yaml` is only safe once every import site is gone (1a) and the seeders/CLI are rewritten against the new model (depends on 1b). The new reindex CLI depends on 1c's single-collection sync.

A useful intermediate guarantee: **after 1a the test suite + `flask` import must still pass against the old DB schema**; after 1b they pass against the new schema with old Typesense; 1c flips search; 1d is pure cleanup.

---

## 2. Deletion manifest (sub-plan 1a)

Everything here is a hard delete or a strip-in-place that does **not** depend on the new model. Cross-references that must be cleaned to avoid dangling imports are listed per group.

### Models (`src/project/models/`)
- **`user.py`**: delete `Company`, `UserCompany`, `CompanyInvitation`, `CompanyBookmark`, helper `CompanySuggestionBuilder` (lines 412–471). Strip columns `User.oauth_provider` (line 94), `User.is_investor_mode_active` (104–106), `UserInfo.refuse_all_invitations` (163–165). Drop `User` relationships `user_companies`, `company_bookmarks`. Keep (do not yet repoint) `investor`/`investor_bookmarks`/`investment_firm_bookmarks`/`claim_*` — those move in 1b. Fix `EmailVerification.expire_all_by_user_id` bug (386–395): set `ev.is_used = True` not `ev.is_expired` (read-only `@property`, 375–378).
- **`investment.py`**: delete `Investment`, `FundingRound` (entire file once routes/admin/schemas that import them are gone). Remove dangling back-refs `Investor.investments`, `InvestmentFirm.investments`, `Round.funding_rounds`.
- **`investor.py`**: delete `SuggestionBuilder`, `get_suggestions`/`get_suggestion_investment_firms`, all `calculate_*_score`, `generate_index_file`, `Investor.populate`/`populate_all`/`populate_cli`, `InvestmentFirm.populate`, `fix_twitter_links`, `update_typesense_collection`, plus `populate_blockchain`. (The model *bodies* of `Investor`/`InvestmentFirm`/`NotableInvestment` and the M2M tables stay — 1b reshapes them.)
- **`__init__.py` (models)**: drop re-exports of `Company`, `UserCompany`, `CompanyInvitation`, `CompanyBookmark`, `Investment`, `FundingRound`.

### Routes (`src/project/routes/`)
- **DELETE files**: `payment.py` (466 ln), `onboarding.py` (262), `investment.py` (238), `profile.py` (146), `admin/company.py` (533), `admin/funding_round.py` (178), `admin/investments.py` (212).
- **STRIP in place**: `main.py` — delete vanity (`eric`/`jennifer`/`arstan` 61–87), `pricing`/`about`/`superconnect`/`faq`, `construction()`, all `company_*`/`get_company*`/`toggle_bookmark_company`; **move** `check_user_info_complete`/`check_verification` into `utils/decorators.py`. `search.py` — delete `search_companies` (`@check_investor_mode`), `get_suggestion_companies`, investor-mode branching (full search collapse is 1c). `settings.py` — delete every company/team/investor-mode/funding-round handler + `plan()`/`billing()` + the `from .payment import get_invoices` (line 58). `claim.py` — strip reCAPTCHA (61, 77–81, 151, 166–170). `auth.py` — delete OAuth (`oauth_user`, `api_call`, google/linkedin/apple login+callback), `tier_selection`, `fetch_time`. `admin/__init__.py` — remove `register_blueprint` for company/funding_round/investments (lines 36, 37, 39).

### Templates (`src/project/templates/`)
- **DELETE**: `onboarding/*`, `payment/index.html`, `settings/billing.html`+`plan.html`, `settings/company*.html`+`create_company.html`+`create_investor.html`, `auth/tier_selection.html`, vanity (`eric/jennifer/arstan/construction/components/gemini/layouts/layout_payment`), marketing (`about/pricing/superconnect/faq/download`), `company*.html`/`search_companies.html`/`suggestions_companies.html`, `investment.html`, `user_profile.html`, `components/onboarding/*`, the company/funding/member component set, admin company/funding/investment templates.
- **STRIP**: `auth/login.html` (OAuth buttons), `index.html` (Medium feed + typewriter/cycle), navbar/aside (OAuth/investor-mode/billing links). Rename `settings/delete_oauth_account.html` → delete-account.

### Static (`src/project/static/`)
- **DELETE all of `vue/`**: `base.js` (658), `main.js` (1041), `settings.js` (1794), `admin.js` (1811), `investorOnboarding.js` (527), `duplicate.js` (332), `history.js` (221), `payment.js` (45). Also `scripts/onboarding.js`, `scripts/typewriter.js`, `scripts/cycle.js`. Strip reCAPTCHA submit from `scripts/claiming/manual.js`. **Cross-ref**: every `<script src=...vue/*.js>` tag + the Vue CDN `[[ ]]` delimiter snippet + PostHog client snippet must be removed from kept templates.

### Utils (`src/project/utils/`)
- **DELETE**: `google_helpers/` (whole dir — `__init__.py`, `google_pubsub.py`, `google_storage.py`), `scraper_helpers/population.py`, `parse_medium.py`, `fake_data.py`. From `suggestion.py` delete `COMPANY_WEIGHTS`. From `decorators.py` delete `check_investor_mode`/`check_investor_mode_for_suggestions`. From `typesense_search.py` delete `setup`, `update_schema`, module-level `search`, `populate_schema_from_file` (cities helpers). Move `add_https_prefix` from `scraper.py` → `funcs.py`.
- **Cross-ref cleanup (import sites)**: `google_pubsub.send_event` — auth.py:39/187, onboarding.py:28/114/218, claim.py:30, settings.py:54, payment.py:22/379/394/411. `google_storage` — settings.py:55, admin/user.py:21, admin/company.py:17. `parse_medium.parse_medium_html` — main.py `index()`. `check_investor_mode` — search.py.

### Deps (`pyproject.toml`) — staged in 1a, finalized in 1d
- Remove: `stripe`, `sendgrid` (dead — zero src imports), `google-cloud-storage`, `google-cloud-pubsub`, `authlib`, `googlemaps`. Re-evaluate `pillow`/`pillow-heif` (only `google_storage.py`). Keep `pyjwt` (Phase 3 magic-link).

### Config — **`src/project/__init__.py` (call out explicitly)**
- Drop `register_blueprint`/import for `payment` (lines 30, 100), `onboarding`, `investment`, `profile`.
- Delete `get_apple_client_secret` (36–62) + its imports `jwt` (6), `itsdangerous.base64_decode` (10), `jwt.exceptions.InvalidKeyError` (11).
- Delete `oauth.init_app(app)` (117) + the 3 `oauth.register` blocks (120–146) + remove `oauth` from `extensions.py` (1, 18) and the `from .extensions import ... oauth` name (15).
- Remove `stripe.api_key`.
- `cloudbuild.yaml`: remove `_GOOGLE_OAUTH2_*`, `_LINKEDIN_OAUTH2_*`, `_STRIPE_*` (39–41), `_SENDGRID_API_KEY` (42), all `_PUBSUB_*` (43–53), `_GOOGLE_MAPS_API_KEY` (54); keep `_DATABASE_URL`, `_TYPESENSE_*` (55–57).
- `enums.py`: delete `OauthProvider`, `Tier` (defer to Phase 4? — keep per UserPayment note), `CompanyRole`; prune `Events` STRIPE_*/COMPANY_INVITATION/USER_COMPLETED_ONBOARDING. (Adding new entity enums is 1b.)

---

## 3. Data-model migration design (sub-plan 1b)

### Target tables (exact columns)

**`person`** (from `Investor` person-half of `InvestorBase`)
`id` PK; `first_name` NOT NULL; `last_name`; `slug` unique; `about`; `position`; `website`; `linkedin`; `twitter`; `email`; `phone_number`; `is_public` NOT NULL default false; `is_approved` NOT NULL default false; `user_id` FK user.id nullable; `search_index`; `created_at`.

**`organization`** (from `InvestmentFirm`)
`id` PK; `name`; `slug` unique; `about`; `website`; `linkedin`; `twitter`; `email` unique; `phone_number`; `n_employees`; `org_type` (enum `org_type`, e.g. firm); `is_public` NOT NULL default true; `search_index`; `created_at`.

**`investor_profile`** (polymorphic person|org; from investment fields of both `Investor` + `InvestmentFirm`)
`id` PK; `entity_type` (enum person|org); `entity_id`; `min_investment` BigInteger; `max_investment` BigInteger; `n_investments`; `n_exits`; `thesis` (text, ← `about` optional); `lead_pref` (enum, nullable); `accepts_cold_inbound` Boolean default false; `is_active` Boolean default true; `investor_type` (enum, nullable). Unique(`entity_type`,`entity_id`).

**`affiliation`** (new edge, replacing `Investor.firm_name`)
`id` PK; `person_id` FK person.id; `organization_id` FK organization.id; `role` (enum `affiliation.role`); Unique(`person_id`,`organization_id`,`role`).

**`geography`** (replacing `location`/`_coordinates`/`_country` + `Country`)
`id` PK; `slug` unique; `type`; `country_code`.

**Polymorphic facet joins** (replace the 12 M2M tables) — each keyed by `(entity_type ENUM person|org, entity_id)`:
- `entity_industry`: + `industry_id` FK industry.id
- `entity_stage`: + `stage` (enum `investment_stage`, seeded from `Round` names Pre-Seed/Seed/Series A/B/C)
- `entity_notable`: + `notable_investment_id` FK notable_investment.id
- `entity_geography`: + `geography_id` FK geography.id

**Kept/reworked lookups**: `Industry` (unchanged, behind `entity_industry`); `Round` → `investment_stage` enum/lookup (drop `funding_rounds` rel); `NotableInvestment` keep but **drop `company_id` FK + `company` relationship**; `Country` → **deleted**, superseded by `geography`.

**Bookmarks**: merge `InvestorBookmark`+`InvestmentFirmBookmark` → one `entity_bookmark(id, user_id, entity_type, entity_id, created_at)`; reimplement `get_by_user_id`/`get_id_list`/`exists` with the discriminator.

### Polymorphic-join decision (flag)
Use a **`(entity_type ENUM('person','org'), entity_id INT)` discriminator pair** on all `entity_*` joins, `investor_profile`, `entity_bookmark`, and the repointed `claim_*` — **not** a shared surrogate `entity` table and **not** dual nullable FKs. Rationale: it matches the Typesense composite-id scheme (`f'{entity_type}_{db_id}'`) one-to-one, avoids a join table per facet per entity, and the discriminator drives the search `entity_type` facet directly. Trade-off accepted: no DB-level FK from `entity_id` to two tables — integrity is enforced in the ORM/app layer (document this).

### Alembic strategy
1. **Additive migration**: create `person`, `organization`, `affiliation`, `investor_profile`, `geography`, `entity_industry/_stage/_notable/_geography`, `entity_bookmark`. Add `investment_stage`/`org_type`/`person_type`/`affiliation.role`/`investor_type` enums. Repoint `claim_verification.investor_id`/`claim_request.investor_id` → `entity_type`+`entity_id` (add new cols, keep old FK temporarily). Seed `geography` from `data/cities_index.jsonl`; seed `investment_stage` from the 5 Round names; seed `industry` via existing `populate_industry`.
2. **Data backfill** (Python within the migration or a one-shot `op.execute`/command — see below).
3. **Destructive migration**: drop the 12 M2M tables, `investor_backup`/`investor_origin_point` (+ their 6 M2M), `investment`, `funding_round` (drop `investment` first — FKs to funding_round/investor/investment_firm — then `funding_round`), `company`/`user_company`/`company_invitation`/`company_bookmark`, `country`, `investor`, `investment_firm`, `investor_bookmark`, `investment_firm_bookmark`. Drop `user.oauth_provider`, `user.is_investor_mode_active`, `user_info.refuse_all_invitations`. Mind the SQLite `PRAGMA foreign_keys=ON` listener (`_set_sqlite_pragma`, user.py:1034–1039) and ondelete ordering.

### Data backfill steps
1. **Person**: one `person` per `Investor`; map `first_name/last_name/slug/about/position/website/linkedin/twitter/email/phone_number/is_public/is_approved/user_id/search_index`. Generate slug via reused `set_slug` uuid-suffix collision logic (drop the `full_name=True` setter footgun).
2. **Organization**: one `organization` per `InvestmentFirm`; map `name/slug/about/website/linkedin/twitter/email/phone_number/n_employees`.
3. **Affiliation**: for each `Investor.firm_name`, fuzzy/exact-match (reuse `thefuzz.fuzz`) against `InvestmentFirm.name` → `affiliation(person_id, organization_id, role)`. Orphan firm_names with no match → **create stub `organization`** rows.
4. **investor_profile**: one row per person and per org from `min_investment/max_investment/n_investments/n_exits` (+ `about`→thesis). Drop `bias` entirely (suggestion-only).
5. **entity_industry / entity_stage / entity_notable**: migrate `investor_*` and `investment_firm_*` M2M rows into the polymorphic joins keyed by the new person/org `entity_id`. **DROP** `investor_backup_*`/`investor_origin_point_*` rows outright. For `entity_stage`, preserve the `Series B+`→{Series B, Series C} expansion from the populate_* methods.
6. **entity_geography**: geocode/lookup each `Investor.location`/`InvestmentFirm.location` against `geography`; **drop coordinates** (only used by deleted distance scoring).
7. **entity_bookmark**: copy `investor_bookmark` rows (entity_type=person) and `investment_firm_bookmark` rows (entity_type=org).
8. **claim_* repoint**: `claim_verification`/`claim_request` rows `investor_id` → `entity_type='person', entity_id=<new person id>`. Refactor `ClaimRequest.get_all`/`get_pending_by_user_id` which use raw `table('User')`/`table('Investor')` literals (break when `investor` dropped).
9. **search_history**: remap `type` column — `investment_firm`→org, `investor`→person; drop `company`.

### Investment / NotableInvestment repointing (flag)
- **`Investment` is DELETED, not repointed.** Its only real anchor is `funding_round_id` → a Company round, both deleted. The pivot's portfolio/deals concept is served entirely by **`NotableInvestment`** behind `entity_notable`. Do not build a portfolio table.
- **`NotableInvestment` is the portfolio source**: keep its rows, drop `company_id` FK + `company` rel, fold its 4 per-entity M2M tables into `entity_notable`.

---

## 4. Typesense migration (sub-plan 1c)

### Single `entities` collection schema
Name `entities`, `primary_key='id'` where `id = f'{entity_type}_{db_id}'`. Fields:
`id`(string), `entity_type`(string, facet) ['person'|'org'], `db_id`(int32, facet), `name`(string), `slug`(string, opt), `about`(string, opt), `position`(string, facet, opt) [person], `org_name`(string, opt) [person's affiliated org — replaces `firm_name`], `person_names`(string[], opt) [org's affiliated people], `website`/`linkedin`/`twitter`(string, opt), `country_code`(string, facet, opt), `geographies`(string[], facet, opt) [geography slugs], `industries`(string[], facet, opt), `stages`(string[], facet, opt) [replaces `rounds`], `notable_investments`(string[], opt), `check_size_min`(int32, opt, sort), `check_size_max`(int32, opt, sort), `lead_pref`(string, facet, opt), `accepts_cold_inbound`(bool, facet, opt), `is_active`(bool, facet, opt), `investor_type`(string, facet, opt), `n_investments`/`n_exits`(int32, opt, sort), `embedding`(float[], `embed.from=[name,about,position,industries,geographies]`, remote Gemini `model_config`).

This replaces the `investors` (investor.py:1081–1120), `investment_firms` (1741–1777), `companies` (user.py:733–768), and `cities` schemas, plus the implicit `industries` collection (investor.py:785).

### v26→v30 + client 2.x breakages
- Bump `typesense>=0.21.0,<1.0.0` → 2.x (+ `typesense-stubs`). Verify `typesense.client.Client`, `typesense.exceptions.ObjectNotFound` import paths.
- `collection.synonyms.*` **removed** → `client.synonym_sets.upsert(...)` (global). Reshape the 134-entry `synonyms` list in `info_lists.py:310–1641` into v30 `{items:[{synonyms:[...]}]}`; reference `synonym_set_names` on the schema/query. New fn `create_synonym_sets()` replaces `create_synonyms`.
- `documents.import_` return shape changed — current code parses `result[0]['document']` JSON string OR `result[0]['id']` dict; normalize for 2.x in `upsert_documents`.
- Local embedder `ts/all-MiniLM-L12-v2` (4 sites) → **Gemini remote** `embed.model_config={model_name:'google/text-embedding-004', api_key:<GEMINI_API_KEY>}`. Verify Typesense server can reach Google.
- Hybrid search: include `embedding` in `query_by` so v30 fuses keyword+vector; make the hardcoded `distance_threshold:0.50` (typesense_search.py:100) configurable. Handle new ranking fields (`text_match_info`, `vector_distance`, rank fusion).

### get_search / SearchBuilder / sync rewrite outline
- Collapse `Investor.get_search` (439–510), `InvestmentFirm.get_search` (1414–1481), `Company.get_search` (delete) into one **`Entity.get_search(entity_type, ...)`** over `entities` with an `entity_type` filter.
- **Fix the `countries` bug**: callers pass `filter_by('countries', ...)` (investor.py:465, 1439) but the schema field is `country` → matched zero docs. Use the new `country_code`/`geographies` field.
- **Remove the broad `except Exception`** swallow (investor.py:477, 1448; user.py:641) — log/re-raise in non-prod.
- **Drop** the `FLASK_ENV=='testing'` hardcoded-empty short-circuit (typesense_search.py:94) in favor of a test mock.
- **Fix `delete_data`**: filter by **both `db_id` AND `entity_type`** to avoid person/org db_id collisions.
- **Fix** `InvestmentFirm.sync_search_index` duplicate-key bug (investor.py:1801–1802 writes `min_investment` twice, drops `max_investment`).
- Collapse the two `sync_search_index` static methods into one **`Entity.sync_search_index(recreate)`** iterating person+org batches; retarget the raw `UPDATE investor/investment_firm SET search_index` SQL to `person`/`organization`.
- `filter_by_boolean` (typesense_search.py:63): replace `is_public`/`is_approved` gate with `accepts_cold_inbound`/`is_active`.
- Replace `cities` setup/geocode with the `geography` table feeding `geographies[]`.

---

## 5. Risks & verification

**Highest-risk steps**
1. **1b destructive migration (irreversible backfill).** The `firm_name`→`affiliation` fuzzy match and the M2M→polymorphic collapse have no clean downgrade once `investor`/`investment_firm` are dropped.
   - *Verify*: (a) Run the additive+backfill migration on a **restored production DB snapshot**, then assert row-count parity: `count(person)==count(investor)`, `count(organization)==count(investment_firm)`, `count(entity_industry)==sum(investor_industry+investment_firm_industry)`, `affiliation` count vs non-null `firm_name`, plus an orphan-stub-org report. (b) Keep the destructive `DROP` migration as a **separate revision** so the additive+backfill can be validated and even run in prod before the drops commit. (c) Snapshot/backup gate before the drop revision.
2. **1c search cutover + Gemini reachability.** A bad embedder config or unreachable Google API silently returns empty results (today masked by the swallow-all except).
   - *Verify*: Build `entities` in a **parallel collection** first; diff hit counts/top-N for a fixed query set against the legacy `investors`/`investment_firms` before flipping route callers in `search.py` (lines 48/62/77/86/129–155/232–255). Confirm the `country`/`country_code` filter now returns non-zero (the historical zero-match bug is the regression baseline).

**Per sub-plan self-verification**
- **1a**: `python -c "import src.project"` + full test suite pass against the **unchanged** DB schema; grep that no kept template references `vue/*`, `layout_payment`, or removed `<script>`; grep no surviving `send_event`/`stripe.`/`oauth.register`/`googlemaps` import.
- **1b**: SQLite in-memory test DB through the additive+backfill+drop chain; ORM smoke tests for `person`/`organization`/`affiliation`/`investor_profile`/`entity_*`; `alembic upgrade head` then `downgrade` on the **additive** revision (drops revision is one-way, document it).
- **1c**: parallel-collection diff harness (above); unit test `Entity.get_search` filter construction (assert `country_code` not `countries`); test `delete_data` only removes the matching `entity_type`.
- **1d**: `uv sync` resolves with deps removed; `flask setup` runs end-to-end on a scratch DB; new reindex CLI runs `sync_search_index(recreate=False)` **without** `db.drop_all` and preserves `search_index` ids.

---

## 6. Recommended first sub-plan to build

**Start with 1a (Strip dead platform).**

Reasons:
- It is the only sub-plan with **no dependency** on any other and the **lowest risk** (deletions + import cleanup, no schema change, no data movement).
- It **shrinks the surface area** every later sub-plan must reason about: ~6.7k lines of Vue, 7 route files, the whole `google_helpers` package, payment/onboarding/investment, and all suggestion/bias scoring vanish — so 1b's ORM rewrite and 1c's search rewrite touch far fewer call sites.
- It produces a **clean, compiling, test-passing checkpoint** against the *existing* DB and Typesense, which de-risks 1b: the destructive migration then runs against a tree whose only remaining consumers of `Investor`/`InvestmentFirm` are the seeders and search code that 1b/1c will rewrite anyway.
- It unblocks the dependency-ordered deletes the scoping data calls for: un-register blueprints in `__init__.py` → delete route files → delete templates/JS → delete now-unreferenced utils, while preserving the shared guards (`check_user_info_complete`/`check_verification`) by relocating them into `utils/decorators.py` first.

Concrete first commit within 1a: relocate the two shared guards into `decorators.py` and repoint `auth/search/settings` imports, then un-register and delete `payment`/`onboarding`/`investment`/`profile` blueprints in `src/project/__init__.py`, then delete `google_helpers/` and excise its 10 `send_event` + 3 `google_storage` call sites.