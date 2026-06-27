# Favicon + meta preview refresh — design

**Date:** 2026-06-27
**Status:** Approved (direction); pending asset build

## Problem

The current favicon (`static/elements/icon.png`) and Open Graph image
(`static/elements/metapreview.png`) predate the "Ledger" redesign. They use the
old bright-cyan accent and a pure-white background, which now clash with the
live brand system (warm paper, ink, deeper brand blue, Fraunces serif). They
are also incomplete: a single PNG `<link rel="icon">` with no SVG favicon,
`.ico` fallback, Apple touch icon, PWA manifest, or `theme-color`.

## Goals

- Refresh both assets into the Ledger palette and keep the distinctive
  "i + dot" mark (the dotted *i* from the `globalify` wordmark).
- Ship a complete, modern favicon set + a 1200×630 OG image.
- Wire the tags into every layout `<head>` via one shared partial (DRY).

Non-goals: changing the wordmark/logo itself, touching email templates, or
altering OG title/description copy.

## Brand tokens (from `tailwind.config.js`)

| token | hex | role |
|-------|-----|------|
| paper | `#FBFAF6` | warm background |
| panel | `#F5F2E9` | secondary surface |
| surface | `#FFFFFF` | cards |
| ink | `#15120B` | near-black text |
| soft | `#544D3C` | secondary text |
| faint | `#8A8470` | muted text |
| rule | `#E6E0D2` | hairlines |
| brand | `#0C72D3` (deep `#0B5BA8`, tint `#E6F0FB`) | accent blue |
| green | `#0E7A4F` (tint `#E7F2EB`) | secondary accent |

Display serif: **Fraunces** (`static/elements/fonts/fraunces-600.woff2`).
Wordmark / sans: **Poppins**. Mono: **Space Mono**.

## Decisions (approved)

- **Style:** match the Ledger redesign.
- **Favicon mark:** "i + dot", treatment **C · Ink** — dark ink tile (`#15120B`),
  paper *i* (`#FBFAF6`), bright blue dot. High contrast at 16px, keeps the
  blue-dot signature, reads on light and dark tab bars.
- **Meta preview text:** "The open investor directory".
- **OG layout:** **2 · Ledger rows** — wordmark + Fraunces tagline + mono
  `globalify.org` on the left; a stack of three stylized investor "ledger
  entries" (avatar, name/firm bars, check-size pill) on the right.
- **Deliverables:** full modern set (below).

## Deliverables

### New / replaced asset files (`src/project/static/elements/`)

| file | size | notes |
|------|------|-------|
| `favicon.svg` | vector | master "i + dot" ink tile; source of truth |
| `favicon.ico` | 16/32/48 | classic fallback, built from PNGs |
| `favicon-96.png` | 96×96 | general PNG icon |
| `apple-touch-icon.png` | 180×180 | iOS home screen (small inner padding) |
| `icon-192.png` | 192×192 | PWA manifest |
| `icon-512.png` | 512×512 | PWA manifest |
| `icon-maskable-512.png` | 512×512 | manifest `purpose: maskable`, ~20% safe-area padding |
| `site.webmanifest` | — | name, short_name, icons, theme/background color |
| `icon.png` | 32×32 | **replaced** (legacy path kept; some refs may exist) |
| `metapreview.png` | 1200×630 | **replaced** in place (preserves canonical OG URL) |

`metapreview.png` keeps its filename so the already-published canonical URL
`https://globalify.org/static/elements/metapreview.png` (cached by social
crawlers, hardcoded in `layout_auth`/`layout_clean`) resolves to the new image
with no template change required for the OG/Twitter image tags.

### `site.webmanifest`

```json
{
  "name": "Globalify",
  "short_name": "Globalify",
  "icons": [
    { "src": "/static/elements/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/elements/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/static/elements/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ],
  "theme_color": "#FBFAF6",
  "background_color": "#FBFAF6",
  "display": "standalone"
}
```

### New partial: `src/project/templates/partials/_favicons.html`

```html
<link rel="icon" href="/static/elements/favicon.ico" sizes="32x32" />
<link rel="icon" type="image/svg+xml" href="/static/elements/favicon.svg" />
<link rel="icon" type="image/png" sizes="96x96" href="/static/elements/favicon-96.png" />
<link rel="apple-touch-icon" href="/static/elements/apple-touch-icon.png" />
<link rel="manifest" href="/static/elements/site.webmanifest" />
<meta name="theme-color" content="#FBFAF6" />
```

This is a static `{% include %}` — no Jinja blocks — so it does not interfere
with the SEO `{% block %}` overrides that base.html requires to stay inline.

### Template edits

In each of `layouts/base.html`, `layouts/layout_auth.html`,
`layouts/layout_admin.html`, `layouts/layout_clean.html`: replace the single
`<link rel="icon" type="image/png" href="/static/elements/icon.png" />` line
with `{% include "partials/_favicons.html" %}`. No other `<head>` changes; the
existing `og:image` / `twitter:image` references continue to point at
`metapreview.png` (now the new image).

## Production method

All rendering uses tools already on the machine (ImageMagick, `sips`, Pillow,
the Playwright browser MCP) — no new dependencies.

**Favicon raster set.** Author `favicon.svg` by hand (rounded ink tile, paper
*i* stem, blue dot — simple rects + circle, resolution-independent). Render it
to a 512×512 PNG via the headless browser (crisp anti-aliasing), then
downscale with ImageMagick/`sips` to 192/96/48/32/16. Build `favicon.ico` from
the 16/32/48 PNGs (`magick`). `apple-touch-icon.png` = the mark on a filled
tile at 180 with slight inner padding; `icon-maskable-512.png` = the mark with
~20% safe-area padding so Android mask crops don't clip it.

**OG image.** Build a self-contained `1200×630` HTML file (the approved
"Ledger rows" layout) with `@font-face` pointing at the local Fraunces woff2
and Poppins, the `globalify` wordmark typeset in Poppins with a brand-blue dot,
and the stylized directory rows. Render with the Playwright MCP at a 1200×630
viewport and screenshot → `metapreview.png`. Verify dimensions are exactly
1200×630.

## Verification

- `magick identify` (or `sips -g pixelWidth -g pixelHeight`) confirms every
  asset's exact dimensions.
- Favicon legibility check at 16px and 32px (visual).
- `site.webmanifest` parses as JSON.
- Grep confirms all four layouts include `partials/_favicons.html` and no stale
  `icon.png` `<link>` remains.
- Load a page locally and confirm the new favicon + OG tags render (browser
  devtools / view-source), and the OG image opens at the canonical path.

## Risks

- ImageMagick SVG rendering can be weak without librsvg; mitigated by rendering
  the master via the headless browser instead and only using ImageMagick for
  raster downscaling and `.ico` assembly.
- Social platforms cache OG images aggressively; replacing `metapreview.png`
  in place is the fastest path to a refreshed preview, but external caches may
  lag (acceptable).
