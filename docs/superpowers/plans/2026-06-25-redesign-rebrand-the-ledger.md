# Redesign & Rebrand — "The Ledger" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Globalify's dated visual design with the approved "Ledger" brand system (design tokens + fonts + components) and rebuild the flagship landing + pricing with Paddle-compliant "self-serve database" copy.

**Architecture:** Define one set of CSS-variable design tokens in `static/src/input.css`, expose them through `tailwind.config.js`, self-host the Fraunces + Space Mono fonts beside Poppins, then restyle the shared chrome (`partials/_nav.html`, `partials/_footer.html`) and rebuild `index.html` + `pricing.html` on the existing `base.html`. Pages still on legacy layouts inherit the system later when Phase 2 reparents them.

**Tech Stack:** Flask + Jinja2, TailwindCSS v3.4 via PostCSS, vanilla JS (`menu.js`), no bundler. Fonts: Fraunces (display serif), Poppins (UI/body, existing), Space Mono (data).

## Global Constraints

- **Design source of truth:** `DESIGN.md` (tokens, type scale, components, bans) and `PRODUCT.md` (positioning, voice). The approved visual reference is `.superpowers/brainstorm/29789-1782381920/content/ledger-landing.html`.
- **Color tokens (hex anchors):** brand `#0C72D3`, brand-deep `#0B5BA8`, brand-tint `#E6F0FB`, green `#0E7A4F`, green-tint `#E7F2EB`, paper `#FBFAF6`, panel `#F5F2E9`, surface `#FFFFFF`, ink `#15120B`, soft `#544D3C`, faint `#8A8470`, rule `#E6E0D2`, rule-2 `#EDE8DC`.
- **Type:** Fraunces (display/headings/wordmark), Poppins (UI/body), Space Mono (labels/figures/timestamps). Never add a 4th family.
- **Copy positioning (Paddle-critical):** Globalify is a **software/data subscription only**. ALLOWED vocabulary: database, records, search, filter, shortlist, export, access, subscription, verified, updated. BANNED vocabulary anywhere in public copy: `introduc*`, `connect you`, `we help`, `fund your`, `raise (capital|money|funding)`, `expert advice`, `course`, `academy`, `mentor`, `advisor`/`advisory`, `success fee`, `matchmak*`, `facilitat*`, `superconnect`.
- **Pricing shown:** Free $0 / Pro **$7 per month**. Frame as "a software subscription to a database. No commissions, no success fees."
- **No em dashes in copy.** Bans (match-and-refuse): gradient text, decorative glassmorphism, side-stripe borders, hero-metric template, identical card grids.
- **Tailwind content glob must remain** `./src/project/templates/**/*.{html,htm}` so new classes are not purged. Rebuild `main.css` after every template batch.
- **Verification reality:** there is no unit-test suite; this is visual/template work. Each task is verified by a successful CSS build, a browser check (Playwright MCP or manual at `http://localhost:5000`), and copy greps. Commit after each task.

---

### Task 1: CSS build, fonts, and design tokens (the foundation)

**Files:**
- Modify: `package.json` is fine as-is; run `npm install` (node_modules currently absent).
- Add: `src/project/static/elements/fonts/Fraunces-*.woff2`, `SpaceMono-*.woff2`
- Modify: `src/project/static/src/input.css` (font-face block + `@layer base` tokens)
- Modify: `tailwind.config.js` (map tokens to Tailwind theme)
- Build artifact: `src/project/static/css/main.css`

**Interfaces:**
- Produces: Tailwind utilities `bg-paper text-ink bg-brand text-brand border-rule bg-panel text-soft text-faint bg-green text-green` etc.; font utilities `font-display` (Fraunces), `font-poppins` (existing), `font-mono` (Space Mono); CSS vars `--brand`, `--paper`, `--ink`, … available globally.

- [ ] **Step 1: Install dependencies and confirm the build runs**

```bash
cd /Users/arstan/Desktop/globalify
npm install
npm run build:css
```
Expected: `main.css` is regenerated (file mtime updates; size changes from the stale committed artifact). No PostCSS errors.

- [ ] **Step 2: Download self-hosted fonts (woff2)**

Use google-webfonts-helper (no API key). Fetch Fraunces (weights 400,500,600; normal + italic) and Space Mono (400,700 normal):

```bash
cd /Users/arstan/Desktop/globalify/src/project/static/elements/fonts
for w in 400 500 600; do
  curl -sL "https://gwfh.mranftl.com/api/fonts/fraunces?download=zip&subsets=latin&variants=${w},${w}italic&formats=woff2" -o "fraunces-${w}.zip" && unzip -o "fraunces-${w}.zip" && rm "fraunces-${w}.zip"
done
curl -sL "https://gwfh.mranftl.com/api/fonts/space-mono?download=zip&subsets=latin&variants=regular,700&formats=woff2" -o "spacemono.zip" && unzip -o spacemono.zip && rm spacemono.zip
ls
```
Expected: `fraunces-*.woff2` and `space-mono-*.woff2` files present. (If gwfh is unreachable, download the same families manually from fonts.google.com and place the `.woff2` files here; adjust the `@font-face` `src` filenames in Step 3 to match.)

- [ ] **Step 3: Add `@font-face` + tokens to `input.css`**

At the top of `src/project/static/src/input.css`, after the existing Poppins `@font-face` block, add (adjust filenames to those downloaded in Step 2):

```css
/* Fraunces — display serif */
@font-face { font-family: "Fraunces"; src: url("/static/elements/fonts/fraunces-400.woff2") format("woff2"); font-weight: 400; font-display: swap; }
@font-face { font-family: "Fraunces"; src: url("/static/elements/fonts/fraunces-400italic.woff2") format("woff2"); font-weight: 400; font-style: italic; font-display: swap; }
@font-face { font-family: "Fraunces"; src: url("/static/elements/fonts/fraunces-500.woff2") format("woff2"); font-weight: 500; font-display: swap; }
@font-face { font-family: "Fraunces"; src: url("/static/elements/fonts/fraunces-600.woff2") format("woff2"); font-weight: 600; font-display: swap; }
@font-face { font-family: "Fraunces"; src: url("/static/elements/fonts/fraunces-600italic.woff2") format("woff2"); font-weight: 600; font-style: italic; font-display: swap; }

/* Space Mono — data/metadata */
@font-face { font-family: "Space Mono"; src: url("/static/elements/fonts/space-mono-v15-latin-regular.woff2") format("woff2"); font-weight: 400; font-display: swap; }
@font-face { font-family: "Space Mono"; src: url("/static/elements/fonts/space-mono-v15-latin-700.woff2") format("woff2"); font-weight: 700; font-display: swap; }
```

In the same file, replace the existing `@layer base { html { font-family: -apple-system, ... } }` block with token definitions + a paper/ink default:

```css
@layer base {
  :root {
    --brand: #0C72D3; --brand-deep: #0B5BA8; --brand-tint: #E6F0FB;
    --green: #0E7A4F; --green-tint: #E7F2EB;
    --paper: #FBFAF6; --panel: #F5F2E9; --surface: #FFFFFF;
    --ink: #15120B; --soft: #544D3C; --faint: #8A8470;
    --rule: #E6E0D2; --rule-2: #EDE8DC;
  }
  html { font-family: "Poppins", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  body { background: var(--paper); color: var(--ink); }
}
```

- [ ] **Step 4: Map tokens in `tailwind.config.js`**

In `tailwind.config.js`, extend `theme.extend.colors` and add `fontFamily`. Replace the existing `colors` block (keeping `deep-purple` is unnecessary; remove it) so it reads:

```js
extend: {
  colors: {
    brand: { DEFAULT: "#0C72D3", deep: "#0B5BA8", tint: "#E6F0FB" },
    green: { DEFAULT: "#0E7A4F", tint: "#E7F2EB" },
    paper: "#FBFAF6", panel: "#F5F2E9", surface: "#FFFFFF",
    ink: "#15120B", soft: "#544D3C", faint: "#8A8470",
    rule: "#E6E0D2", "rule-2": "#EDE8DC",
  },
  fontFamily: {
    display: ['"Fraunces"', "serif"],
    poppins: ['"Poppins"', "sans-serif"],
    mono: ['"Space Mono"', "ui-monospace", "monospace"],
  },
  maxWidth: { "8xl": "90rem" },
  // ...keep existing animation/keyframes
},
```

- [ ] **Step 5: Rebuild CSS and verify tokens resolve**

```bash
cd /Users/arstan/Desktop/globalify
npm run build:css
grep -c "Fraunces" src/project/static/css/main.css
grep -c "0C72D3\|#0c72d3" src/project/static/css/main.css
```
Expected: build succeeds; both greps return ≥1 (font + a utility using brand exist once a template uses them — if 0 for the color, that is fine until Task 3 adds `bg-brand`; the font grep must be ≥1).

- [ ] **Step 6: Commit**

```bash
git add package-lock.json src/project/static/elements/fonts src/project/static/src/input.css tailwind.config.js src/project/static/css/main.css
git commit -m "feat(design): add Ledger design tokens, Fraunces + Space Mono fonts, fix CSS build"
```

---

### Task 2: Wire fonts + paper background into `base.html`

**Files:**
- Modify: `src/project/templates/layouts/base.html` (preload links in `<head>`, body class)

**Interfaces:**
- Consumes: fonts + tokens from Task 1.
- Produces: every page on `base.html` renders on paper/ink with fonts preloaded.

- [ ] **Step 1: Add font preloads**

In `base.html` `<head>`, beside the existing Poppins `<link rel="preload">`, add:

```html
<link rel="preload" href="/static/elements/fonts/fraunces-600.woff2" as="font" type="font/woff2" crossorigin />
<link rel="preload" href="/static/elements/fonts/space-mono-v15-latin-regular.woff2" as="font" type="font/woff2" crossorigin />
```

- [ ] **Step 2: Set body base classes**

Change the `<body>` tag from `class="font-poppins w-full {% block body_class %}{% endblock %}"` to:

```html
<body class="font-poppins w-full bg-paper text-ink {% block body_class %}{% endblock %}">
```

- [ ] **Step 3: Rebuild + verify in browser**

```bash
npm run build:css && source start.sh   # then load http://localhost:5000/404 in a browser/Playwright
```
Expected: the 404 page (already on base.html via layout_error) renders on warm paper with Poppins; no console errors; Fraunces/Space Mono requested in the network tab.

- [ ] **Step 4: Commit**

```bash
git add src/project/templates/layouts/base.html
git commit -m "feat(design): load Ledger fonts and paper background in base layout"
```

---

### Task 3: Rebuild `partials/_nav.html` (Ledger chrome)

**Files:**
- Modify: `src/project/templates/partials/_nav.html`

**Interfaces:**
- Consumes: tokens + fonts (Task 1). Keeps `menu.js` contract (`#menu`, `openMenu()`, `closeMenu()`), keeps `current_user` auth branches and links (`/investors`, `/firms`, `/pricing`, `/login`, `/settings`).
- Produces: the `Globalify ᴰᴮ` wordmark markup reused by the footer (Task 4).

- [ ] **Step 1: Replace the wordmark + desktop nav**

Replace the logo `<a>` (the `<img logo-black.png>` + BETA span) in BOTH the top bar and the mobile drawer with the Fraunces wordmark:

```html
<a href="/" class="flex items-baseline gap-0.5" aria-label="Globalify home">
  <span class="font-display text-2xl font-semibold tracking-tight text-ink">Globalify</span>
  <sup class="font-mono text-[9px] font-bold tracking-widest text-brand">DB</sup>
</a>
```

Add `/pricing` to the desktop links list and restyle links to Ledger:

```html
<ul class="hidden gap-7 md:flex list-none" role="list">
  <li><a href="/investors" class="font-poppins text-sm font-medium text-soft hover:text-ink transition-colors">Investors</a></li>
  <li><a href="/firms" class="font-poppins text-sm font-medium text-soft hover:text-ink transition-colors">Firms</a></li>
  <li><a href="/pricing" class="font-poppins text-sm font-medium text-soft hover:text-ink transition-colors">Pricing</a></li>
</ul>
```

- [ ] **Step 2: Restyle the CTA buttons**

Replace `bg-sky-500 ... hover:bg-sky-400` rounded-full pills with the ink button (both desktop + mobile drawer; keep the `current_user` if/else):

```html
<a href="/login" class="font-poppins inline-flex items-center justify-center rounded-[11px] bg-ink px-4 py-2 text-sm font-semibold text-paper transition-colors hover:bg-black">Log in</a>
```
(Authenticated branch: same classes, href `/settings`, label `My account`.) Update the nav container border from `border-gray-100` to `border-rule`, and the mobile drawer links' `hover:bg-slate-100` to `hover:bg-panel`, `text-gray-900` to `text-ink`.

- [ ] **Step 3: Rebuild + verify**

```bash
npm run build:css   # reload / on a browser
```
Expected: nav shows `Globalify ᴰᴮ` in serif, three links incl. Pricing, an ink Log in button on paper, hairline bottom border. Mobile hamburger still opens/closes the drawer.

- [ ] **Step 4: Commit**

```bash
git add src/project/templates/partials/_nav.html src/project/static/css/main.css
git commit -m "feat(design): Ledger nav with Globalify DB wordmark"
```

---

### Task 4: Rebuild `partials/_footer.html` (Ledger + Paddle-safe copy)

**Files:**
- Modify: `src/project/templates/partials/_footer.html`

**Interfaces:**
- Consumes: tokens (Task 1), wordmark markup (Task 3).

- [ ] **Step 1: Replace the footer shell, tagline, and colophon**

Replace the `<footer class="bg-[#1D1539] ...">` opening with a paper footer with a top rule, swap the `<img globalify.png>` brand block for the wordmark, and replace the tagline `Use Globalify — Fund Your Startup` (BANNED copy) with:

```html
<footer class="border-t border-rule bg-paper text-soft" aria-labelledby="footer-heading">
  <h2 id="footer-heading" class="sr-only">Footer</h2>
  <div class="mx-auto max-w-7xl px-8 pb-8 pt-16">
    <!-- brand column -->
    <a href="/" class="flex items-baseline gap-0.5" aria-label="Globalify home">
      <span class="font-display text-xl font-semibold text-ink">Globalify</span>
      <sup class="font-mono text-[8px] font-bold tracking-widest text-brand">DB</sup>
    </a>
    <p class="mt-3 max-w-xs text-sm text-soft">A verified, self-serve database of investors and venture firms.</p>
```
Keep the existing social SVGs (Instagram/Twitter/LinkedIn) but set their wrapper text color to `text-faint hover:text-ink`.

- [ ] **Step 2: Fix columns + colophon**

Set column headings to `font-mono text-[10.5px] uppercase tracking-wider text-faint`, links to `text-sm text-soft hover:text-ink`. Keep columns: **Product** (Investors, Firms, Pricing), **Company** (About, Blog, Contact), **Legal** (Privacy, Terms, Refunds). Replace the `© 2024 Globalify. All rights reserved.` line with:

```html
<div class="mt-12 flex items-center justify-between border-t border-rule pt-6 font-mono text-[11px] uppercase tracking-wide text-faint">
  <span>© 2026 Globalify</span>
  <span>A self-serve investor database</span>
</div>
```

- [ ] **Step 3: Rebuild + verify + copy grep**

```bash
npm run build:css
grep -niE "fund your|introduc|advisor|superconnect|course|academy" src/project/templates/partials/_footer.html
```
Expected: footer renders on paper with the wordmark + colophon; grep returns NOTHING.

- [ ] **Step 4: Commit**

```bash
git add src/project/templates/partials/_footer.html src/project/static/css/main.css
git commit -m "feat(design): Ledger footer, remove non-compliant tagline"
```

---

### Task 5: Rebuild `index.html` as the Ledger flagship landing

**Files:**
- Modify: `src/project/templates/index.html` (full rewrite of the `{% block content %}` and the SEO blocks)

**Interfaces:**
- Consumes: tokens/fonts (Task 1), nav/footer (Tasks 3–4). Keeps `extends "layouts/base.html"` and the search `<form action="/search" method="get">` with `#results` (used by existing search JS) — restyled, not removed.

**Visual source of truth:** `.superpowers/brainstorm/29789-1782381920/content/ledger-landing.html`. Port each section to Tailwind utilities using the Task 1 tokens (`bg-paper`, `text-ink`, `font-display`, `font-mono`, `border-rule`, `bg-brand`, `text-brand`, `text-green`, `bg-panel`). Sections, in order:

1. **Ticker** — `font-mono text-[10.5px] text-faint` row with hairline bottom border: `INVESTORS 12,431 · FIRMS 4,512 · COUNTRIES 90 · NEW·7D +182` (the `+182` in `text-green`), right-aligned `LAST SYNC TODAY 06:00 UTC`. (Figures may be hardcoded for now; a later task can wire real counts.)
2. **Hero** — two-column on `lg`: left = `font-mono` kicker `THE INVESTOR RECORD · VOL. 1`, `font-display` h1 `Every investor, <em class="italic text-brand">on the record.</em>` (`text-5xl lg:text-6xl`), `text-soft` lead, an ink primary button "Search the database" + a `text-ink` link with `border-b-2 border-brand` "See pricing", and a `font-mono text-faint` note `// free to search · no introductions, no advisors, no success fees`. Right = the **record card** (white `bg-surface` rounded-2xl, mono header `RECORD · 04412` + `● VERIFIED` in green, identity row, `field → value` rows, last row `Contact → 🔒 Unlock with Pro` in brand).
3. **Search section** — keep the existing `<form action="/search">` and `#results` div, restyled: `rounded-2xl border border-rule bg-surface`, brand submit. Remove the rainbow "magic" suggestions gradient icon (replace its link with a plain `text-faint` icon or drop it).
4. **Credibility line** — centered `font-display text-xl text-soft`: `12,431 investors · 4,512 firms · 90 countries, ` + `text-green` `verified and updated daily.`
5. **Numbered index** ("A database, not a middleman.") — 3 ruled columns `01/02/03` (`font-mono text-brand` numbers, `font-display` h3, `text-soft` body): Verified records / Search & filters / Export & track. NOT identical cards.
6. **Ledger table preview** ("Inside the database.") — `bg-surface` rounded-2xl with mono uppercase `bg-panel` table head (Name, Stage, Sector, Check, Status, Contact), 4 ruled rows, `● verified` in green, `Unlock` in brand.
7. **Pricing teaser** ("Subscription access.") — Free $0 vs Pro **$7/month** (`bg-panel` Pro with `RECOMMENDED` badge), foot line `A software subscription to a database. Cancel anytime · no commissions · no success fees.`
8. **Final CTA** — `bg-ink text-paper` rounded-3xl band, `font-display` `The whole world of investment, <em class="italic text-[#7FB8EE]">on the record.</em>`, paper button "Search the database".

DELETE entirely from the old `index.html`: the SuperConnect case-study carousel (Qubic/ClimateX/OliveX/Cambrian), the "Tailored experience / Experts" + `countries.svg` section, the testimonials carousel, the "From the blog / expert advice" section, and the "Free Startup Course / Knowledge Hub" section. KEEP (restyled, optional): the "We are NOT hiring" anti-scam notice — convert to paper/ink/`border-rule`; it is not marketing copy.

- [ ] **Step 1: Update the SEO block + replace content**

Set `{% block title %}The investor database for founders{% endblock %}` and `{% block meta_description %}Search 12,000+ investors and venture firms by stage, sector and geography. A self-serve database. Filter, shortlist and export.{% endblock %}`. Replace the whole `{% block content %}…{% endblock %}` with the 8 sections above (port markup from the visual source of truth, swapping its raw `<style>` classes for the Tailwind token utilities).

- [ ] **Step 2: Rebuild + browser verify**

```bash
npm run build:css   # reload http://localhost:5000/
```
Expected: the landing matches the approved Ledger reference (ticker, serif hero + record card, numbered index, ledger table, $0/$7 pricing, dark CTA). Zero console errors. Search box still submits to `/search`.

- [ ] **Step 3: Copy compliance grep (must be clean)**

```bash
grep -niE "introduc|connect you|we help|fund your|raise (capital|money|funding)|expert advice|course|academy|mentor|advisor|success fee|matchmak|facilitat|superconnect" src/project/templates/index.html
```
Expected: NO output.

- [ ] **Step 4: Commit**

```bash
git add src/project/templates/index.html src/project/static/css/main.css
git commit -m "feat(design): rebuild landing as Ledger, remove advisory positioning"
```

---

### Task 6: Restyle `pricing.html` + Paddle-safe pricing copy

**Files:**
- Modify: `src/project/templates/pricing.html`

**Interfaces:**
- Consumes: tokens/fonts, nav/footer. Stays on `base.html`.

- [ ] **Step 1: Apply Ledger system + correct plans**

Restyle the page to paper/ink with a `font-display` heading "Subscription access." and the two-plan block from the landing (Free $0 / Pro **$7/month**, `bg-panel` Pro card with `RECOMMENDED` badge). Ensure every benefit line is product/data framed (search, browse, unlock contacts, unlimited bookmarks, CSV export). Add the foot line `A software subscription to a database. Cancel anytime. No commissions, no success fees.` Preserve any existing Stripe/Paddle checkout `action`/route and CSRF hidden input already in the template.

- [ ] **Step 2: Rebuild + verify + copy grep**

```bash
npm run build:css
grep -niE "introduc|we help|fund your|raise (capital|money|funding)|expert advice|course|mentor|advisor|success fee|facilitat" src/project/templates/pricing.html
```
Expected: pricing renders in Ledger style with $7 Pro; grep returns NOTHING; checkout button still posts to its existing route.

- [ ] **Step 3: Commit**

```bash
git add src/project/templates/pricing.html src/project/static/css/main.css
git commit -m "feat(design): Ledger pricing page, software-subscription framing"
```

---

### Task 7: Paddle copy pass on legal pages (Terms, Refund)

**Files:**
- Modify: `src/project/templates/terms_of_service.html`, `src/project/templates/refund_policy.html`

**Interfaces:** none (copy-only; these pages are still on the legacy standalone layout and will be reparented by Phase 2 — do NOT restyle them now, only fix product-description language).

- [ ] **Step 1: Align the product description with "software subscription"**

In both files, find any clause describing what Globalify provides/sells. Ensure it reads as **access to a software database on a subscription** (e.g. "Globalify provides a subscription to a searchable database of investor and firm information"). Remove or reword any sentence describing advisory, consulting, introductions, fundraising assistance, or success-fee/commission arrangements. Do not alter unrelated legal boilerplate.

- [ ] **Step 2: Copy grep across the whole public surface (gate for Paddle re-submission)**

```bash
cd /Users/arstan/Desktop/globalify
grep -rniE "introduc|connect you to|we help you|fund your startup|raise (capital|money|funding)|expert advice|free startup course|academy|mentor|advisory|success fee|matchmak|facilitat|superconnect" \
  src/project/templates/index.html src/project/templates/pricing.html \
  src/project/templates/terms_of_service.html src/project/templates/refund_policy.html \
  src/project/templates/partials/_footer.html src/project/templates/partials/_nav.html
```
Expected: NO output. (If any line is legitimate non-marketing legal text, review individually; the intent is zero advisory/brokerage positioning.)

- [ ] **Step 3: Commit**

```bash
git add src/project/templates/terms_of_service.html src/project/templates/refund_policy.html
git commit -m "chore(copy): describe Globalify as a software subscription for Paddle compliance"
```

---

### Task 8: Final build, visual + accessibility verification

**Files:** none (verification only)

- [ ] **Step 1: Clean build + dead-token check**

```bash
cd /Users/arstan/Desktop/globalify
npm run build:css
grep -rc "sky-500\|sky-400" src/project/templates/index.html src/project/templates/pricing.html src/project/templates/partials/_nav.html src/project/templates/partials/_footer.html
```
Expected: build clean; the rebuilt files return `0` for legacy `sky-*` usage.

- [ ] **Step 2: Browser verification (Playwright MCP or manual)**

Load `/`, `/pricing`, `/404`. For each: confirm the Ledger system renders (paper, Fraunces headings, Space Mono data, Ocean/emerald accents), zero console errors, and AA contrast on body text and the dark CTA band. Confirm nav/footer wordmark and mobile menu work.

- [ ] **Step 3: Commit any build artifact**

```bash
git add src/project/static/css/main.css
git commit -m "build(css): regenerate main.css for Ledger rollout" || echo "nothing to commit"
```

---

## Self-Review

- **Spec coverage:** Foundation/tokens/fonts (Task 1–2) ✓; consistency via shared chrome (Task 3–4) ✓; flagship landing (Task 5) ✓; Paddle copy repositioning across landing/pricing/legal + audit grep (Tasks 5–7) ✓; pricing $7 + subscription framing (Task 6) ✓; verification incl. contrast + console (Task 8) ✓. Out-of-scope items (profiles, browse, search, settings, admin restyle) are intentionally deferred to Phase 2 reparenting per the spec §5.3.
- **Deferred, by design:** wiring real ticker/stat counts (hardcoded for now), and reparenting legacy standalone templates onto `base.html`.
- **Type/name consistency:** token names (`brand`, `paper`, `ink`, `panel`, `rule`, `green`, `font-display`, `font-mono`) are defined in Task 1 and used identically in Tasks 2–8.
