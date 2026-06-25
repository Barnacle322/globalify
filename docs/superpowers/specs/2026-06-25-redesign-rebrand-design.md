# Globalify Redesign & Rebrand — "The Ledger"

Date: 2026-06-25
Status: Approved direction, pending implementation plan
Related: `PRODUCT.md`, `DESIGN.md`, `docs/phase-2-planning-brief.md`

## 1. Goal

Replace Globalify's dated, inconsistent visual design with a single, modern,
distinctive brand system ("The Ledger"), proven on a flagship landing page and
then rolled out across the site. Two hard requirements sit alongside the
aesthetic goal:

1. **Consistency.** The site currently runs 4–5 parallel layout/design systems
   (a half-finished `base.html` + `partials/` migration alongside older
   standalone templates). The redesign must collapse onto one system.
2. **Payments compliance (Paddle).** Paddle rejected `globalify.org` as
   "Human Services / Consulting or Advisory Services." The rebrand must
   reposition Globalify as a **pure self-serve software/data subscription** and
   strip all advisory / brokerage / course / matchmaking language across the
   whole public domain so the domain can be re-submitted and approved.

## 2. Decisions (locked with the user)

- **Ambition:** bold redesign, with blue + roundness + the Poppins lineage as
  anchors. New visual language, stronger personality.
- **Approach:** flagship landing page first to define the language, then extract
  tokens/components and roll out.
- **Personality:** premium & trustworthy, expressed as an **editorial financial
  record** ("The Ledger"), not generic SaaS.
- **Direction chosen** from three mocked options (Ledger / Terminal / Atlas):
  **The Ledger.**
- **Palette:** primary **Ocean blue `#0C72D3`**; **emerald `#0E7A4F`** as a narrow
  verified/value signal; warm paper/ink neutrals. Full tokens in `DESIGN.md`.
- **Type:** **Fraunces** (serif display) + **Poppins** (UI/body, retained) +
  **Space Mono** (data/metadata).
- **Wordmark:** `Globalify` (Fraunces 600) with a Space Mono `DB` superscript.
- **Pricing shown:** Free $0 / **Pro $7 per month**, framed explicitly as "a
  software subscription to a database. No commissions, no success fees."

The approved flagship mockup lives at
`.superpowers/brainstorm/<session>/content/ledger-landing.html` (reference only;
not production code).

## 3. Repositioning (copy) requirements

The redesign is also a copy rewrite. Across **all public pages** (landing,
pricing, terms of service, refund policy, privacy, profiles, browse):

- **Lead with:** database, records, search, filter, shortlist, export, access,
  subscription, verified, updated.
- **Remove everywhere:** "introduce / introducing", "connect you to investors",
  "we help you raise", "fund your startup", "expert advice", "course / academy",
  "SuperConnect", "mentor", "advisor", "success fee", matchmaking framing.
- **Known offenders to delete/rewrite** (from current `index.html`): the
  SuperConnect case-study section (~l.162–215, "Globalify backed the vision by
  introducing…"), "Learn how to grow your business with our expert advice"
  (~l.358), the "course" block (~l.405). Footer links to SuperConnect / Academy /
  Digest are removed.
- Terms of Service and Refund Policy must describe a **software subscription**
  (access to a database), since Paddle re-reviews the entire domain.

## 4. Visual system

Authoritative source: `DESIGN.md`. Summary:

- **Color strategy:** Restrained — warm tinted neutrals, Ocean blue as the single
  ~10% accent, emerald < 5% for verified/unlocked/value only. OKLCH tokens with
  hex anchors.
- **Type scale:** Fraunces display (60/42/34/20), Poppins body (16/14/13.5),
  Space Mono labels (10.5–11, uppercase, tracked). ≥1.25 between steps.
- **Structure:** hairline rules over shadows; asymmetric hero; no card-grid
  reflex (ruled numbered index instead); generous radii (cards 16–18, buttons
  10–11, pills 999).
- **Signature components:** record card, masthead ticker, ledger table, numbered
  index, button set, `Globalify ᴰᴮ` wordmark.
- **Bans:** gradient text, decorative glassmorphism, side-stripe borders,
  hero-metric template, identical card grids, em dashes in copy.
- **Motion:** ease-out-expo, fades + ≤8px translateY, reduced-motion respected.

## 5. Architecture & rollout

### 5.1 Foundation (the substrate everything inherits)
- **Fix the CSS build** (`npm install`; regenerate `main.css` — currently a stale
  artifact) so changes are verifiable.
- **Design tokens:** define CSS variables in `static/src/input.css` and map them
  in `tailwind.config.js` (`colors.brand`, `colors.paper`, `colors.ink`,
  `colors.green`, …). This replaces the scattered `sky-*` (90+ uses), stray
  `blue-*`, and inline hex blues with one source of truth.
- **Fonts:** self-host Fraunces + Space Mono `woff2` alongside Poppins under
  `static/elements/fonts/`; `@font-face` in `input.css`; preload hero Fraunces.
- **Shared chrome:** restyle `partials/_nav.html` (`Globalify ᴰᴮ` wordmark, ticker
  optional) and `partials/_footer.html` (Ledger footer + colophon, Paddle-safe
  links) so every page on `base.html` updates at once.

### 5.2 Flagship landing
- Rebuild `index.html` (on `base.html`) as the full Ledger landing: ticker, hero +
  record card, credibility line, numbered index, ledger-table product preview,
  $0/$7 pricing, dark CTA, footer. Carries the repositioned copy.

### 5.3 Rollout order (coordinate with `phase-2-planning-brief.md`)
The redesign and the Phase 2 SSR/SEO migration are complementary; the token +
component layer here is exactly Phase 2's "2a foundation." To avoid throwaway
work, **apply the system to pages as they live on `base.html`**, and let the
remaining standalone pages (search, investor/firm, settings, admin, legal) adopt
it when Phase 2 reparents them, rather than hand-restyling doomed templates now.
Priority after the landing: pricing, profiles (person/organization), browse,
auth/login, errors, then legal pages (also a Paddle copy fix), then app/admin.

## 6. Out of scope (for now)

- Rewriting routes/models/search (owned by Phase 2 sub-plans 2b–2e).
- Admin/settings visual polish until those pages are reparented onto `base.html`.
- New product features. This is design system + copy repositioning only.

## 7. Verification

- `npm run css` builds; tokens resolve; no purge drops (content glob still
  `./src/project/templates/**/*.{html,htm}`).
- Playwright: `/` (and each migrated page) renders with the new system, zero
  console errors, AA contrast on paper and the dark CTA band.
- **Copy audit:** grep the public templates for the banned advisory/brokerage/
  course vocabulary (section 3) and confirm zero hits before Paddle re-submission.
- Visual spot-check against the approved `ledger-landing.html` reference.
