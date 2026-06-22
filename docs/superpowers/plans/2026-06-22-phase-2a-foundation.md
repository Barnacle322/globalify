# Phase 2a — Foundation: CSS build + base layout + SSR partials

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Fix the broken Tailwind build, create ONE parameterized base layout + shared partials + JSON-LD scaffolding, and reparent the salvageable static pages onto it — the substrate every later Phase 2 sub-plan extends. Verify rendering live with Playwright.

**Architecture:** A single `layouts/base.html` with named blocks replaces the 5 layouts + the ~11 pages that duplicate their own `<head>`. Shared partials (`_nav`, `_footer`, `_head_meta`, `_analytics`) and JSON-LD partials are includable by all later pages. Tailwind v3.4 build is repaired (`npm install` + regenerate the stale `main.css`); the content glob must scan the new template dirs. Design reference: **`docs/phase-2-planning-brief.md` §1 (2a), §2, §5**.

**Tech Stack:** Flask + Jinja2, Tailwind v3.4 (PostCSS), htmx (self-hosted, added in 2e — not here), Playwright (verification).

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never `main`.
- **CSS:** stay on Tailwind v3.4 (no v4 churn). The `css` npm script is `npx postcss ./src/project/static/src/input.css -o ./src/project/static/css/main.css`. The content glob must include `./src/project/templates/**/*.{html,htm}` so new `partials/`, `profiles/`, `browse/` dirs are scanned (classes purge otherwise). Regenerate `main.css` after template changes (the committed one is a stale Feb-2025 artifact).
- **No Vue / no CDN JS.** Do not reintroduce Vue or `[[ ]]` delimiters. Analytics (PostHog) goes in `_analytics.html` behind a config flag (`settings`); don't hardcode keys.
- **SSR, crawlable:** content must be in the server-rendered HTML. Base layout includes `<link main.css>`, font preload, and a `{% block scripts %}` (htmx include added in 2e).
- **Scope:** 2a only does the build fix + base layout + partials + reparenting the SALVAGE set (`index`, `privacy_policy`, `terms_of_service`, `errors/*`, `auth/login`). Do NOT build profile/browse/facet pages (2b/2c) or touch models/admin (2d).
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run pytest` green (69+5); `uv run ruff check . && uv run ruff format --check .` clean; app imports; `npm run css` (one-shot, not `--watch`) builds without error.
- **Commits:** conventional subject; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: Repair CSS build + create base layout, partials & JSON-LD scaffolding

**Files:**
- `npm install` (regenerate `node_modules`); confirm one-shot build: `npx postcss ./src/project/static/src/input.css -o ./src/project/static/css/main.css` (no `--watch`). Add a one-shot `npm run build:css` script alongside the existing watch `css` script.
- `tailwind.config.js`: confirm/repair the content glob includes `./src/project/templates/**/*.{html,htm}` and `./src/project/static/**/*.js`; remove dead `view-eric/jennifer/arstan` safelist/classes + dead animations if present.
- Create `src/project/templates/layouts/base.html` with blocks: `title`, `meta_description`, `canonical`, `og` (default OG tags overridable), `json_ld`, `head_extra`, `body_class`, `content`, `scripts`. Include `_head_meta`, `_nav`, `_footer`, `_analytics`.
- Create partials: `templates/partials/_head_meta.html` (charset/viewport/title/description/canonical/OG/Twitter, using blocks/vars with sensible defaults + the real favicon), `_nav.html` (public nav — logo, Investors, Firms, login/account; no OAuth/investor-mode/billing links), `_footer.html` (privacy/terms/links), `_analytics.html` (PostHog snippet wrapped in `{% if config/settings posthog key %}`).
- Create JSON-LD partials (macros or includes that take a context object): `templates/partials/_jsonld_person.html`, `_jsonld_organization.html`, `_jsonld_breadcrumb.html`, `_jsonld_itemlist.html` — each emits a `<script type="application/ld+json">` block. They can be stubs that accept the expected vars (filled when 2b/2c pass real data); ensure they render valid empty/minimal JSON when given no data so including them never breaks a page.

**Interfaces (produced):** `base.html` block names above; partial include paths; the JSON-LD partial variable contracts (document them in a comment at the top of each partial).

- [ ] **Step 1:** `npm install`; run the one-shot PostCSS build; confirm `main.css` regenerates without error. Add the `build:css` script.
- [ ] **Step 2:** Verify/fix the Tailwind content glob; prune dead classes.
- [ ] **Step 3:** Create `base.html` + the 4 partials + the 4 JSON-LD partials per the specs above. Keep markup clean, semantic, accessible (lang, landmarks, alt text).
- [ ] **Step 4:** Create a tiny throwaway route OR use an existing reparented page to confirm `base.html` renders (deferred to Task 2's reparenting — here just ensure the templates are syntactically valid Jinja: `uv run python -c "from jinja2 import Environment, FileSystemLoader; ..."` or rely on Task 2).
- [ ] **Step 5: Gate** (pytest green, ruff clean, `npm run build:css` succeeds, app imports).
- [ ] **Step 6: Commit** (`feat(ui): repair Tailwind build; add base layout, shared + JSON-LD partials`).

---

## Task 2: Reparent salvage pages onto base + Playwright verification

**Files:** rewrite to `{% extends "layouts/base.html" %}`: `templates/index.html`, `templates/privacy_policy.html`, `templates/terms_of_service.html`, `templates/errors/{400,401,403,404,500,503}.html`, `templates/auth/login.html`. Remove their duplicated `<head>`/PostHog/Vue/`menu.js` includes. Delete obviously-dead `static/elements/*` only if clearly unreferenced (verify with grep first). Regenerate `main.css`.

- [ ] **Step 1:** Reparent each salvage page onto `base.html`, moving page content into `{% block content %}` and setting `title`/`meta_description`/`canonical` blocks. Strip dead `<head>`/Vue/analytics duplication (now centralized).
- [ ] **Step 2:** Regenerate `main.css` (`npm run build:css`) so any classes in the rewritten pages are present.
- [ ] **Step 3:** Gate (pytest green, ruff clean, app imports).
- [ ] **Step 4: Playwright verification.** Start the app locally (`FLASK_ENV=debug SECRET_KEY=x _DATABASE_URL=sqlite:///pw.db uv run flask --app project run -p 5005` after `db.create_all` via `flask shell` or a one-off; if DB-backed pages are hard to seed, verify the static pages). Using Playwright MCP: `browser_navigate` to `/`, `/privacy-policy`, `/terms-of-service`, and a 404 path; `browser_snapshot` to confirm content renders; `browser_console_messages` to confirm ZERO console errors (catches orphaned-Vue regressions); `browser_evaluate` to assert `document.title`, `meta[name=description]`, and `link[rel=canonical]` exist on `/`. Report what you verified. Stop the server afterward.
- [ ] **Step 5: Commit** (`feat(ui): reparent home/privacy/terms/errors/login onto base layout`).

---

## Self-Review

**Coverage (brief §1 2a):** CSS build repair (T1) · base layout + shared partials + JSON-LD scaffolding (T1) · reparent salvage pages (T2) · Playwright verification (T2). 

**Deferred (later Phase 2 sub-plans):** profile/browse pages (2b), facet pages + sitemaps (2c), admin rewire + catalog drop (2d), htmx sprinkles + filters + magic-link auth (2e). `layout_app.html` deletion is blocked until 2b/2d move the last pages off it — do NOT delete it here.

**Risk control:** 2a touches only static/salvage pages + the layout substrate (no models, no routing logic, no admin), so it's low-risk and independently shippable; Playwright proves the base layout + build end-to-end before the data-driven pages build on it.
