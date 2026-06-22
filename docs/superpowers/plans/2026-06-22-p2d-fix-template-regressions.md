# Template Regression Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix HTTP 500 regressions caused by templates still accessing removed legacy attributes (`investor.rounds`, `investor.industries`, `claim_request.investor.slug`, etc.) after the Person/Organization model pivot.

**Architecture:** Four templates need their broken attribute accesses replaced with data from `load_profile_bundle()` (returned as `stages`, `industries`, `profile`, `affiliations`, `geographies`). The admin claim-requests route must resolve target names/slugs before rendering. The deleted `components/create_investment.html` include must be removed from two templates. New smoke tests (no-500 GETs of fixed pages) complete the fix.

**Tech Stack:** Flask/Jinja2, SQLAlchemy 2 (mapped_column dataclass models), pytest, uv

## Global Constraints

- Branch: `revamp/pivot-design`
- All `uv run pytest` must pass (131 prior + new tests)
- `uv run ruff check . --fix && uv run ruff format .` must be clean
- Commit trailer: `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
- New model: `Person`/`Organization` have NO `.rounds`/`.industries`/`.firm_name`/`.position`/`.location`/`.min_investment`/`.max_investment`/`.n_investments`/`.n_exits` on Person
- Profile facets are in `InvestorProfile` (`.min_investment`, `.max_investment`, `.n_investments`, `.n_exits`)
- Stages come from `load_profile_bundle()['stages']` — list of `InvestmentStage` enum values
- Industries come from `load_profile_bundle()['industries']` — list of `Industry` ORM objects
- `ClaimRequest` has `.entity_type`/`.entity_id` (NOT `.investor`)
- Deleted component: `components/create_investment.html` (no longer exists)

---

### Task 1: Fix settings/general.html template + route

**Files:**
- Modify: `src/project/routes/settings.py` — `index` function
- Modify: `src/project/templates/settings/general.html`

**Interfaces:**
- Consumes: `load_profile_bundle(EntityType.PERSON, person.id)` → `{profile, industries, stages, geographies, affiliations}`
- Produces: Template receives `stages`, `industries`, `profile`, `affiliations`, `geographies` alongside `investor=person`

- [ ] **Step 1: Fix `settings.py` `index` route to pass profile bundle**

  In `src/project/routes/settings.py`, update the `index` function:
  - Import `load_profile_bundle` from `..models.entity`
  - Call `load_profile_bundle(EntityType.PERSON, investor.id)` if `investor` is not None
  - Pass `stages`, `industries`, `profile`, `affiliations`, `geographies` to `render_template`
  - Keep `rounds=Round.get_all()` in place (template still needs it for the rounds dropdown, but use `stages` for checked state)

- [ ] **Step 2: Fix `general.html` legacy attribute accesses**

  Replace:
  - `{% if round in investor.rounds %}` → `{% if round.name in stages | map(attribute='value') | list %}` — but `stages` are `InvestmentStage` enum values (strings), so compare `round.name` with stage values. Actually `Round` is legacy and `stages` are `InvestmentStage` enum values — the checkbox comparison is now: render all rounds unchecked (no mapping between legacy `Round` and `InvestmentStage`). Simplest fix: always render unchecked since there is no mapping.
  - `{% for industry in investor.industries %}` → `{% for industry in industries %}`
  - `{% if industry not in investor.industries %}` → `{% if industry not in industries %}`
  - `investor.firm_name` → first affiliation's org name, or blank: `{{ (affiliations[0].organization.name if affiliations else '') }}`
  - `investor.position` → `investor.headline`
  - `investor.location` → first geography name: `{{ (geographies[0].name if geographies else '') }}`
  - `investor.n_investments` → `{{ profile.n_investments if profile else '' }}`
  - `investor.n_exits` → `{{ profile.n_exits if profile else '' }}`
  - `investor.min_investment` → `{{ profile.min_investment if profile else '' }}`
  - `investor.max_investment` → `{{ profile.max_investment if profile else '' }}`
  - `claim_request.investor.slug` → remove/blank (claim_requests pending block no longer can show investor link without resolution; show entity_type/entity_id info or just status)
  - `claim_request.investor.full_name` → remove/blank
  - Remove the `{% import "components/create_investment.html" %}` and its render call
  - Remove the `{% import "components/delete_investment.html" %}` (not deleted but only used with create_investment)
  - Remove the `{% import "components/update_investment.html" %}` and its render call

- [ ] **Step 3: Run tests to confirm regression is captured**

  ```bash
  cd /Users/arstan/Desktop/globalify && uv run pytest tests/test_authenticated_pages.py -v 2>/dev/null || echo "test file not yet created"
  ```

### Task 2: Fix admin/claim_requests.html + route

**Files:**
- Modify: `src/project/routes/admin/__init__.py` — `claim_requests_view` function
- Modify: `src/project/templates/admin/claim_requests.html`

**Interfaces:**
- Consumes: `ClaimRequest.entity_type`, `ClaimRequest.entity_id` → resolve to `Person`/`Organization`
- Produces: Template receives `claim_requests` where each has `.target_name` and `.target_slug` injected

- [ ] **Step 1: Fix `claim_requests_view` route**

  Annotate each claim_request with `target_name` and `target_slug` before rendering:
  ```python
  from ...models.entity import Person, Organization
  from ...utils.enums import EntityType
  
  for cr in claim_requests:
      if cr.entity_type == EntityType.PERSON and cr.entity_id:
          entity = Person.get_by_id(cr.entity_id)
          cr.target_name = entity.full_name if entity else f"Person #{cr.entity_id}"
          cr.target_slug = entity.slug if entity else ""
      elif cr.entity_type == EntityType.ORG and cr.entity_id:
          entity = Organization.get_by_id(cr.entity_id)
          cr.target_name = entity.name if entity else f"Org #{cr.entity_id}"
          cr.target_slug = entity.slug if entity else ""
      else:
          cr.target_name = "Unknown"
          cr.target_slug = ""
  ```

- [ ] **Step 2: Fix `claim_requests.html`**

  Replace:
  - `<a href="/investor/{{claim_request.investor.slug}}"` → `<a href="/investor/{{claim_request.target_slug}}"`
  - `{{ claim_request.investor.full_name }}` → `{{ claim_request.target_name }}`

### Task 3: Fix admin/update_investor.html

**Files:**
- Modify: `src/project/routes/admin/investor.py` — `update_investor_view` function
- Modify: `src/project/templates/admin/update_investor.html`

**Interfaces:**
- Consumes: `load_profile_bundle(EntityType.PERSON, person.id)` → `{profile, industries, stages}`
- Produces: Template receives `stages`, `industries`, `profile` alongside `investor=person`

- [ ] **Step 1: Fix `update_investor_view` route**

  - Import `load_profile_bundle` from `...models.entity`
  - Call bundle and pass `stages`, `industries`, `profile` to template
  - Remove `rounds=Round.get_all()` and `industries=Industry.get_all()` (replaced by bundle)

- [ ] **Step 2: Fix `update_investor.html`**

  - Remove `{% import "components/create_investment.html" ... %}` and its `{{ create_investment.render(...) }}`
  - Remove `<create-investment-component ...>` Vue component usage in the HTML body
  - Remove `{% import "components/delete_investment.html" %}` and its `{{ delete_investment.render() }}`  
  - Remove `{% import "components/update_investment.html" %}` and its `{{ update_investment.render(...) }}`
  - Replace `{% if round in investor.rounds %}` → always render unchecked (no rounds mapping)
  - Replace `{% for industry in investor.industries %}` → `{% for industry in industries %}`
  - Replace `{% if industry not in investor.industries %}` → `{% if industry not in industries %}`
  - Replace `investor.firm_name` → `''` (graceful blank)
  - Replace `investor.position` → `''`
  - Replace `investor.location` → `''`
  - Replace `investor.n_investments` → `{{ profile.n_investments if profile else '' }}`
  - Replace `investor.n_exits` → `{{ profile.n_exits if profile else '' }}`
  - Replace `investor.min_investment` → `{{ profile.min_investment if profile else '' }}`
  - Replace `investor.max_investment` → `{{ profile.max_investment if profile else '' }}`

### Task 4: Fix admin/update_investment_firm.html

**Files:**
- Modify: `src/project/routes/admin/investment_firm.py` — `update_investment_firm_view`
- Modify: `src/project/templates/admin/update_investment_firm.html`

**Interfaces:**
- Consumes: `load_profile_bundle(EntityType.ORG, org.id)` → `{profile, industries, stages}`
- Produces: Template receives `stages`, `industries`, `profile` alongside `investment_firm=org`

- [ ] **Step 1: Fix `update_investment_firm_view` route**

  - Import `load_profile_bundle`
  - Call bundle and pass `stages`, `industries`, `profile`
  - Remove `rounds=Round.get_all()` and `industries=Industry.get_all()`

- [ ] **Step 2: Fix `update_investment_firm.html`**

  - Remove BOTH `{% import "components/create_investment.html" %}` lines (there are two)
  - Remove `{{ create_investment.render(...) }}`
  - Remove `{% import "components/delete_investment.html" %}` and render call
  - Remove `{% import "components/update_investment.html" %}` and render call
  - Remove `<create-investment-component ...>` body references
  - Replace `{% if round in investment_firm.rounds %}` → always unchecked
  - Replace `{% for industry in investment_firm.industries %}` → `{% for industry in industries %}`
  - Replace `{% if industry not in investment_firm.industries %}` → `{% if industry not in industries %}`
  - Replace `investment_firm.location` → `''`
  - Replace `investment_firm.n_investments` → `{{ profile.n_investments if profile else '' }}`
  - Replace `investment_firm.n_exits` → `{{ profile.n_exits if profile else '' }}`
  - Replace `investment_firm.min_investment` → `{{ profile.min_investment if profile else '' }}`
  - Replace `investment_firm.max_investment` → `{{ profile.max_investment if profile else '' }}`

### Task 5: Add render smoke tests

**Files:**
- Create: `tests/test_authenticated_pages.py`

- [ ] **Step 1: Write the smoke tests**

  Tests must:
  - Create an in-memory SQLite DB, create all tables
  - Seed: User (regular, verified) + UserInfo + UserPayment; User (admin, verified) + UserInfo + UserPayment
  - Seed: Person (linked to regular user), Organization, ClaimRequest (entity_type=PERSON)
  - Log in regular user via `session["_user_id"]`
  - Log in admin user via `session["_user_id"]`
  - GET `/settings/general` as regular user → assert != 500
  - GET `/admin/claim-requests` as admin → assert != 500
  - GET `/admin/investors/<id>` as admin → assert != 500
  - GET `/admin/investment-firms/<id>` as admin → assert != 500

- [ ] **Step 2: Run tests and confirm pass**

  ```bash
  cd /Users/arstan/Desktop/globalify && uv run pytest tests/test_authenticated_pages.py -v
  ```

### Task 6: Lint, format, full test run, commit

- [ ] **Step 1: Lint and format**

  ```bash
  cd /Users/arstan/Desktop/globalify && uv run ruff check . --fix && uv run ruff format .
  ```

- [ ] **Step 2: Full test run**

  ```bash
  cd /Users/arstan/Desktop/globalify && uv run pytest -v
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add src/project/routes/settings.py src/project/routes/admin/__init__.py src/project/routes/admin/investor.py src/project/routes/admin/investment_firm.py src/project/templates/settings/general.html src/project/templates/admin/claim_requests.html src/project/templates/admin/update_investor.html src/project/templates/admin/update_investment_firm.html tests/test_authenticated_pages.py
  git commit -m "fix: repair template regressions after Person/Organization pivot"
  ```
