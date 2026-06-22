# Phase 1a — Strip Dead Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Delete the dead platform (OAuth, Stripe, GCS, Pub/Sub, reCAPTCHA, googlemaps, the Vue SPA, companies/onboarding/funding/investment/payment/profile routes+templates, suggestion/matching code) and clean every dangling reference — leaving a compiling, test-passing tree with the **old** `Investor`/`InvestmentFirm` catalog model still intact (Phase 1b reshapes it).

**Architecture:** Mechanical, ordered deletion. The authoritative file-and-symbol manifest is **`docs/phase-1-planning-brief.md` §2 (Deletion manifest)** — implementers MUST read it; this plan structures the work into 4 ordered clusters and defines the verification gate. The brief uses line numbers that may have shifted (Phase 0 + earlier tasks edited some files), so implementers verify symbols by name, not by line.

**Tech Stack:** Python 3.14, Flask, SQLAlchemy, `uv`, pytest, ruff.

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never commit to `main`.
- **The catalog stays:** do NOT touch the bodies of `Investor`, `InvestmentFirm`, `NotableInvestment`, or their M2M tables, nor `sync_search_index`/`get_search`/`SearchBuilder` — those are Phase 1b/1c. This plan only removes the *dead platform*, not the catalog/search.
- **Verification gate (every task ends with all four green):**
  1. App imports: `uv run python -c "import sys; sys.path.insert(0,'src'); import project"` exits 0 (set env: `FLASK_ENV=testing SECRET_KEY=x` and, until Task 2 removes the googlemaps import, `_GOOGLE_MAPS_API_KEY=AIzatest`).
  2. `uv run ruff check . && uv run ruff format --check .` clean (run `ruff check . --fix` for unused-import cleanup).
  3. `uv run pytest` green.
  4. No dangling refs: the task's "grep-clean" checks (below) return nothing.
- **Templates/JS:** delete the dead ones and remove Vue SPA wiring. Do NOT hand-perfect surviving templates' nav links — Phase 2 rebuilds the frontend SSR. A surviving template referencing a deleted `url_for` is acceptable (no test renders it); just don't leave dead `<script src="...vue/*">` tags or deleted-blueprint registrations.
- **Commits:** conventional subject; end every message with:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## Task 1: Strip dead routes, blueprints, OAuth & reCAPTCHA

Remove the route-layer dead code. After this, `create_app` registers only the surviving blueprints and no OAuth/Apple/reCAPTCHA code remains.

**Manifest:** `docs/phase-1-planning-brief.md` §2 → "Routes", "Config (`src/project/__init__.py`)", and the reCAPTCHA bits under "Routes". Specifically:
- **Delete route files:** `routes/payment.py`, `routes/onboarding.py`, `routes/investment.py`, `routes/profile.py`, `routes/admin/company.py`, `routes/admin/funding_round.py`, `routes/admin/investments.py`.
- **`src/project/__init__.py`:** remove imports + `register_blueprint` for `payment`, `onboarding`, `investment`, `profile`; delete `get_apple_client_secret` + its now-unused imports (`jwt`, `itsdangerous.base64_decode`, `jwt.exceptions.InvalidKeyError`, `time`); delete `oauth.init_app(app)` + the 3 `oauth.register(...)` blocks.
- **`routes/admin/__init__.py`:** remove `register_blueprint` for `company`, `funding_round`, `investments` (+ their imports).
- **`extensions.py`:** remove `oauth` (the `OAuth` import + the `oauth = OAuth()` line).
- **`routes/auth.py`:** delete OAuth routes/helpers (`oauth_user`, `api_call`, google/linkedin/apple login+callback handlers), `tier_selection`, `fetch_time`. Keep email/password-less-relevant scaffolding and `EmailVerification` usage that survives.
- **`routes/claim.py`:** strip reCAPTCHA (the `_GOOGLE_RECAPTCHA_*` reads, the `siteverify` POST, the `captcha_site_key` template args).
- **Guards:** verify where `check_user_info_complete` / `check_verification` live (likely already in `utils/decorators.py`). If `main.py` or elsewhere defines duplicates, consolidate into `utils/decorators.py` and repoint imports. Delete `check_investor_mode` / `check_investor_mode_for_suggestions` from `decorators.py`.
- **Smoke test:** `tests/test_smoke.py::test_expected_blueprints_registered` — remove `"profile"` from the expected set (and confirm `payment`/`onboarding`/`investment` were never asserted).

**Files:** delete the 7 route files; modify `src/project/__init__.py`, `routes/admin/__init__.py`, `extensions.py`, `routes/auth.py`, `routes/claim.py`, `utils/decorators.py`, `tests/test_smoke.py`.

- [ ] **Step 1: Read the manifest** — read `docs/phase-1-planning-brief.md` §2 fully.
- [ ] **Step 2: Delete the 7 route files** (`git rm`).
- [ ] **Step 3: Edit `__init__.py`, `admin/__init__.py`, `extensions.py`** to drop the registrations/imports/OAuth/Apple code listed above.
- [ ] **Step 4: Strip OAuth from `auth.py` and reCAPTCHA from `claim.py`**; consolidate/clean guards in `decorators.py`.
- [ ] **Step 5: Update the smoke test** (drop `"profile"`).
- [ ] **Step 6: Run the gate** — the 4 checks above. Grep-clean: `grep -rn "oauth.register\|get_apple_client_secret\|recaptcha\|RECAPTCHA\|check_investor_mode\|register_blueprint(profile\|register_blueprint(payment\|register_blueprint(onboarding\|register_blueprint(investment" src/` returns nothing.
- [ ] **Step 7: Commit** (`refactor: strip dead routes, OAuth, reCAPTCHA`).

---

## Task 2: Strip integrations (GCS/PubSub/Maps) + remaining dead handlers in settings/main/search

Delete the Google integration packages and the suggestion engine, excise their call sites in surviving files, and remove the company/onboarding/investor-mode/billing/funding/marketing handlers from the big surviving route files. Simplify the test harness now that the import-time clients are gone.

**Manifest:** `docs/phase-1-planning-brief.md` §2 → "Utils" (incl. the cross-ref import sites list) and the `settings.py`/`main.py`/`search.py` items under "Routes → STRIP in place".
- **Delete:** `utils/google_helpers/` (whole dir), `utils/suggestion.py`, `utils/scraper_helpers/population.py`, `utils/parse_medium.py`, `utils/fake_data.py`.
- **Excise call sites of `send_event`** (now that `payment.py`/`onboarding.py` are gone, remaining: `auth.py`, `claim.py`, `settings.py`) — remove the email-send calls (magic-link/Resend restores sending in Phase 3; for now the verification email simply isn't dispatched). **Excise `google_storage`** sites in `settings.py`, `admin/user.py`. **Excise `parse_medium`** in `main.py index()`. **Excise `gmaps`/`googlemaps`** (was in `suggestion.py`, now deleted).
- **`settings.py`:** delete every company/team/investor-mode/funding-round/billing handler + `plan()`/`billing()` + `from .payment import get_invoices`. Keep account-management handlers (profile edit, account deletion, bookmarks, search history).
- **`main.py`:** delete vanity routes (`eric`/`jennifer`/`arstan`), `pricing`/`about`/`superconnect`/`faq`/`construction`, all `company_*`/`get_company*`/`toggle_bookmark_company`, and the Medium-feed fetch in `index()`.
- **`search.py`:** delete `search_companies`, `get_suggestion_companies`, and investor-mode branching (leave the investor/firm search paths working against the OLD model — full collapse is Phase 1c).
- **Test harness:** `tests/conftest.py` — remove the `pubsub_v1.PublisherClient.from_service_account_info` monkeypatch and the `_GOOGLE_MAPS_API_KEY` env default (both obsolete once the modules importing them are deleted).

**Files:** delete `utils/google_helpers/` + the 4 util files; modify `routes/auth.py`, `routes/claim.py`, `routes/settings.py`, `routes/main.py`, `routes/search.py`, `routes/admin/user.py`, `tests/conftest.py`, and any `__init__`/import sites.

- [ ] **Step 1: Delete the integration + suggestion + scraper util files** (`git rm`).
- [ ] **Step 2: Excise the call sites** (`send_event`, `google_storage`, `parse_medium`, `gmaps`) in the surviving files per the cross-ref list.
- [ ] **Step 3: Strip the dead handlers** from `settings.py`, `main.py`, `search.py`.
- [ ] **Step 4: Simplify `tests/conftest.py`** (remove the pubsub patch + maps env).
- [ ] **Step 5: Run the gate.** Grep-clean: `grep -rn "google_helpers\|send_event\|google_storage\|googlemaps\|parse_medium\|from .payment\|search_companies\|check_investor_mode\|SuggestionBuilder" src/` returns nothing.
- [ ] **Step 6: Commit** (`refactor: remove GCS/PubSub/Maps integrations and dead settings/main/search handlers`).

---

## Task 3: Delete dead models, columns & enums

Remove the platform models and the columns/relationships/enums that referenced them. The catalog models (`Investor`/`InvestmentFirm`/`NotableInvestment`) stay; only their dead *back-references* to deleted models are removed.

**Manifest:** `docs/phase-1-planning-brief.md` §2 → "Models" and the `enums.py` item under "Config".
- **`models/user.py`:** delete `Company`, `UserCompany`, `CompanyInvitation`, `CompanyBookmark`, `CompanySuggestionBuilder`. Strip columns `User.oauth_provider`, `User.is_investor_mode_active`, `UserInfo.refuse_all_invitations`. Drop `User` relationships `user_companies`, `company_bookmarks`. Fix the `EmailVerification.expire_all_by_user_id` bug: set `ev.is_used = True` (it currently writes the read-only `is_expired` property). Keep `investor`/`investor_bookmarks`/`investment_firm_bookmarks`/`claim_*` relationships (Phase 1b repoints them).
- **`models/investment.py`:** delete `Investment` and `FundingRound` (whole file). Remove the now-dangling back-refs `Investor.investments`, `InvestmentFirm.investments`, `Round.funding_rounds`.
- **`models/investor.py`:** delete only the *dead methods* listed in the brief (`SuggestionBuilder`, `get_suggestions`, `calculate_*_score`, `generate_index_file`, `Investor.populate`/`populate_all`/`populate_cli`, `InvestmentFirm.populate`, `fix_twitter_links`, `update_typesense_collection`, `populate_blockchain`). **Do NOT** touch model column definitions, `sync_search_index`, `get_search`, `get_batches`, `populate_demo`, `populate_vcsheet`, `slugify_existing` (1b/1c own those).
- **`models/__init__.py`:** drop re-exports of `Company`, `UserCompany`, `CompanyInvitation`, `CompanyBookmark`, `Investment`, `FundingRound`.
- **`utils/enums.py`:** delete `OauthProvider`, `CompanyRole`; prune dead `Events` members (STRIPE_*, COMPANY_INVITATION, USER_COMPLETED_ONBOARDING). Keep `Tier` (UserPayment still references it until Phase 4) and `SearchHistoryType`, `RequestStatus`.
- Note: the `setup` CLI in `__init__.py` references `Investor.populate_demo`/`InvestmentFirm.populate_vcsheet` — those survive, so `setup` still works. (Its rewrite is Phase 1d.)

**Files:** delete `models/investment.py`; modify `models/user.py`, `models/investor.py`, `models/__init__.py`, `utils/enums.py`.

- [ ] **Step 1: Delete `models/investment.py`** and remove its `__init__.py` exports + the dangling back-refs in `investor.py`.
- [ ] **Step 2: Delete the Company* models + CompanySuggestionBuilder** from `user.py`; strip the dead User/UserInfo columns + relationships; fix the `expire_all_by_user_id` bug.
- [ ] **Step 3: Delete the dead methods** in `investor.py` (leave columns/sync/get_search/seeders alone).
- [ ] **Step 4: Prune `enums.py`** and `models/__init__.py` exports.
- [ ] **Step 5: Run the gate.** Grep-clean: `grep -rn "class Company\|class UserCompany\|class Investment\b\|class FundingRound\|OauthProvider\|CompanyRole\|user_companies\|company_bookmarks\|\.investments\b" src/project/models src/project/utils` returns nothing (allow matches inside comments only).
- [ ] **Step 6: Commit** (`refactor: delete company/investment/funding models, dead methods, OAuth enums; fix expire_all bug`).

---

## Task 4: Delete dead frontend assets, dead dependencies & prune config

Remove the Vue SPA and dead templates/scripts, strip Vue wiring from surviving templates, drop the now-unused dependencies, and prune deployment config.

**Manifest:** `docs/phase-1-planning-brief.md` §2 → "Templates", "Static", "Deps", "Config (cloudbuild)".
- **Delete `static/vue/`** entirely (`base.js`, `main.js`, `settings.js`, `admin.js`, `investorOnboarding.js`, `duplicate.js`, `history.js`, `payment.js`) and dead `static/scripts/` (`onboarding.js`, `typewriter.js`, `cycle.js`).
- **Delete dead templates:** `onboarding/*`, `payment/*`, `settings/billing.html`+`plan.html`+`company*`+`create_company.html`+`create_investor.html`, `auth/tier_selection.html`, vanity (`eric.html`/`jennifer.html`/`arstan.html`/`construction.html`/`gemini.html`), `layouts/layout_payment.html`, marketing (`about.html`/`pricing.html`/`superconnect.html`/`faq.html`/`download.html`), `company*.html`/`search_companies.html`/`suggestions_companies.html`/`investment.html`/`user_profile.html`, `components/onboarding/*`, and the admin company/funding/investment templates.
- **Strip from surviving templates:** every `<script src="...vue/*.js">` tag and the Vue CDN `[[ ]]` delimiter setup and the typewriter/cycle/Medium-feed snippets. Remove OAuth buttons from `auth/login.html`. (Do not otherwise redesign — Phase 2.)
- **Deps (`pyproject.toml`):** remove `stripe`, `sendgrid`, `google-cloud-storage`, `google-cloud-pubsub`, `authlib`, `googlemaps` (use `uv remove`). Re-evaluate `pillow`/`pillow-heif`: keep only if still imported (after `google_storage.py` deletion they likely aren't — remove if `grep -rn "import PIL\|from PIL\|pillow_heif" src/` is empty). Keep `pyjwt` (Phase 3 magic-link).
- **`cloudbuild.yaml`:** remove `_GOOGLE_OAUTH2_*`, `_LINKEDIN_OAUTH2_*`, `_STRIPE_*`, `_SENDGRID_API_KEY`, all `_PUBSUB_*`, `_GOOGLE_MAPS_API_KEY` from `--set-env-vars`; keep `_DATABASE_URL`, `_TYPESENSE_*`.

**Files:** delete `static/vue/*`, dead `static/scripts/*`, the dead templates; modify surviving templates, `pyproject.toml`, `uv.lock`, `cloudbuild.yaml`.

- [ ] **Step 1: Delete `static/vue/` + dead scripts + dead templates** (`git rm`).
- [ ] **Step 2: Strip Vue/CDN/typewriter/Medium snippets + OAuth buttons** from surviving templates (grep for `vue/` and `[[ ]]` and `g-recaptcha` and OAuth provider names across `templates/` and remove).
- [ ] **Step 3: Remove dead deps** (`uv remove stripe sendgrid google-cloud-storage google-cloud-pubsub authlib googlemaps`; conditionally `pillow pillow-heif`) and `uv sync`.
- [ ] **Step 4: Prune `cloudbuild.yaml`** env vars.
- [ ] **Step 5: Run the gate.** Grep-clean: `grep -rn "vue/\|cdn.jsdelivr.*vue\|g-recaptcha" src/project/templates` returns nothing; `grep -rn "stripe\|sendgrid\|google.cloud\|authlib\|googlemaps" src/ pyproject.toml` returns nothing.
- [ ] **Step 6: Commit** (`refactor: delete Vue SPA, dead templates, dead deps; prune cloudbuild env`).

---

## Self-Review

**Spec coverage (Phase 1a per the brief §2):** routes/blueprints (T1) · OAuth+reCAPTCHA (T1) · integrations GCS/PubSub/Maps + suggestion (T2) · settings/main/search dead handlers (T2) · dead models+columns+enums (T3) · `expire_all` bug fix (T3) · Vue SPA + dead templates (T4) · dead deps + cloudbuild (T4). The catalog model + search are explicitly untouched (Phase 1b/1c). ✅

**Out of scope (deferred, not gaps):** data-model consolidation/migration (1b), Typesense v30/single-collection (1c), `flask setup` rewrite + reindex CLI + final enum/dep polish (1d), frontend rebuild (Phase 2).

**Ordering:** T1 (routes) → T2 (integrations + route-body handlers) → T3 (models, after their usages are gone) → T4 (assets/deps, after all Python imports are clean). Each task's gate keeps the tree importable + tested at every commit.
