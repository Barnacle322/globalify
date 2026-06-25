# Design

Visual system for Globalify — "The Ledger": an editorial, financial-record
aesthetic. Premium and trustworthy, the database shown as an authoritative system
of record. Pairs with `PRODUCT.md` (strategy) and `CLAUDE.md` (engineering).

## Theme

Light, warm-paper default. The physical scene: a founder researching investors at
a desk in daylight, treating the screen like a reference work they trust. Warm
off-white paper, ink text, hairline rules. One dark band (the closing CTA) for
punctuation. Not a dark app; not stark white.

## Color

Strategy: **Restrained.** Tinted warm neutrals carry the surface; Ocean blue is
the single primary accent (~10%); emerald is a narrow signal color for
"verified / unlocked / value" only. Values given in OKLCH (source of truth) with
hex anchors used in the current mockups.

### Neutrals (warm, tinted toward paper — never pure #000/#fff)
- `paper`     — `oklch(0.985 0.006 95)` · `#FBFAF6` — page background
- `panel`     — `oklch(0.960 0.012 95)` · `#F5F2E9` — recessed panels, Pro plan, table head
- `surface`   — `oklch(0.995 0.003 95)` · `#FFFFFF` — record cards, raised surfaces
- `ink`       — `oklch(0.205 0.008 75)` · `#15120B` — primary text, dark CTA band
- `soft`      — `oklch(0.430 0.018 80)` · `#544D3C` — body / secondary text
- `faint`     — `oklch(0.610 0.018 90)` · `#8A8470` — mono labels, captions, metadata
- `rule`      — `oklch(0.905 0.012 90)` · `#E6E0D2` — primary hairline divider
- `rule-2`    — `oklch(0.930 0.010 90)` · `#EDE8DC` — lighter inner divider

### Brand — Ocean blue (primary accent)
- `brand`      — `oklch(0.575 0.165 252)` · `#0C72D3` — links, primary buttons, kickers, focus
- `brand-deep` — `oklch(0.480 0.140 252)` · `#0B5BA8` — hover / pressed
- `brand-tint` — `oklch(0.950 0.025 252)` · `#E6F0FB` — soft fills, eyebrow chips

### Signal — Emerald (verified / unlocked / value, <5% of surface)
- `green`      — `oklch(0.550 0.130 158)` · `#0E7A4F` — verified ●, "no fees", upticks
- `green-tint` — `oklch(0.950 0.030 158)` · `#E7F2EB` — verified chip fills

Avatar/identity swatches may use saturated gradients (blue, emerald, indigo,
amber) as data color; keep them inside avatars/marks, not chrome.

## Typography

Three families, each with a job. Do not introduce a fourth.

- **Fraunces** (serif, optical sizing) — display: h1/h2/h3, the wordmark, pull
  quotes. Weights 500–600. *Italic* (not color, not underline) is the primary
  emphasis device in headlines. This face carries the identity.
- **Poppins** (geometric sans) — UI and body: paragraphs, buttons, nav, form
  controls. Weights 300–600. The existing workhorse font, kept.
- **Space Mono** (monospace) — data and metadata: field labels, figures,
  kickers/eyebrows, timestamps, the ticker, table headers, the colophon. This is
  what makes the product read as "a record." Use sparingly and only for data.

### Scale (≥1.25 steps; don't flatten)
- Display XL — Fraunces 60 / line 1.0 / tracking -0.025em (hero h1)
- Display L  — Fraunces 42 (final CTA)
- Heading    — Fraunces 34 (section h2)
- Subhead    — Fraunces 20 (h3, record name)
- Lead       — Poppins 16 / line 1.6
- Body       — Poppins 14 / 13.5
- Label/mono — Space Mono 10.5–11 / tracking 0.08–0.16em / UPPERCASE for eyebrows

Body measure capped at 65–75ch (leads ~40ch by design).

## Layout & Elevation

- **Hairline rules over shadows.** 1px `rule` lines are the primary structural
  device (ticker, nav, section dividers, table rows, the 01/02/03 index). Shadows
  are reserved for genuinely floating cards: `0 18–24px 50–70px rgba(21,18,11,.08–.10)`.
- **Asymmetry and rhythm.** Hero is a 1.12 / 0.88 split (copy + record card). Vary
  section padding; do not pad everything equally.
- **No card-grid reflex.** Features are a ruled numbered index, not three
  identical cards. The product preview is a real table, not card tiles. Never nest
  cards.
- **Radii (generous, the inherited roundness):** cards/panels 16–18px, buttons
  10–11px, small chips/inputs 9px, pills/badges 999px.
- Max content width ~ 1040–1100px, generous gutters.

## Signature components

- **Record card** — white surface, mono header `RECORD · ####` + green `● VERIFIED`,
  identity row (avatar + Fraunces name + mono sub), then `field → value` rows with
  mono uppercase keys; locked rows show `🔒 Unlock with Pro` in brand.
- **Masthead ticker** — thin top bar, mono figures (investors / firms / countries /
  new-7d / last-sync), upticks in green.
- **Ledger table** — the browse/product surface: mono uppercase headers on `panel`,
  ruled rows, verified status, brand "Unlock" for gated contact.
- **Numbered index** — ruled 01/02/03 columns with Fraunces subheads for "what you
  get" type content.
- **Buttons** — `btn-brand` (Ocean fill, white), `btn-ink` (ink fill, paper text),
  `btn-link` (ink text + 2px brand underline), `btn-outline` (1px ink border).
- **Wordmark** — `Globalify` in Fraunces 600 with a Space Mono `DB` superscript.

## Motion

Enhancement only; content is complete without it. Ease-out-expo / quint; no
bounce, no elastic. Fades + small (≤8px) translateY on scroll-in. Never animate
layout properties. Respect `prefers-reduced-motion: reduce`.

## Implementation notes

- Tailwind v3 (existing). Express tokens as CSS variables in `static/src/input.css`
  and map them in `tailwind.config.js` (e.g. `colors.brand`, `colors.paper`,
  `colors.ink`) so utilities replace the scattered `sky-*` / inline hex blues.
- Self-host Fraunces, Poppins, Space Mono as `woff2` under
  `static/elements/fonts/`; preload the hero Fraunces weight. Keep `@font-face`
  in `input.css`.
- Bans (match-and-refuse): gradient text, decorative glassmorphism,
  side-stripe (`border-left` accent) borders, the big-number hero-metric template,
  identical repeated card grids, em dashes in copy.
