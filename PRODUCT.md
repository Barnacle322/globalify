# Product

## Register

product

> Note: the root register is `product` — most surfaces (browse, search, profiles,
> settings, admin) are an app that *serves* the product. The marketing surfaces
> (landing, pricing) are a **brand** register and carry the fullest expression of
> the Ledger identity. Override to `brand` when working on those pages.

## Users

Founders and operators actively raising venture capital, plus the people who run
that process for them (fundraising leads, chiefs of staff, accelerator program
managers). They arrive mid-fundraise with a concrete job: build a shortlist of
relevant investors and reach them directly. They are time-pressed, somewhat
sophisticated about the funding landscape, and skeptical of "we'll connect you"
middlemen. They want to do the research themselves, fast, and trust the data.

## Product Purpose

Globalify is a **self-serve database of investors and venture firms**. Users
search and filter 12,000+ investors by stage, sector, geography and check size,
open structured and verified profiles, unlock contact details with a Pro
subscription, and export shortlists to run their own outreach.

It exists so a founder can do professional-grade investor research without hiring
an advisor, broker, or agency. Success is a visitor finding and shortlisting
relevant investors within minutes and subscribing for full contact access.

**Positioning is load-bearing and a compliance requirement.** Globalify sells a
**software / data subscription only**. It is explicitly NOT an advisory,
consulting, brokerage, matchmaking, introductions, mentorship, course, or managed
"done-for-you" service. Our merchant-of-record (Paddle) rejected the domain when
the site read as "consulting / advisory services," so every public word must
describe a database product: *search, filter, records, access, subscription* —
never *introduce, connect you to, raise for you, expert advice, course, success
fee*. This constraint applies across the whole public domain (landing, pricing,
terms, refunds), not just the homepage.

## Brand Personality

Authoritative, precise, current. The voice of a **financial record or reference
work**, not a growth-marketing pitch: factual, understated, confident. It states
what is in the database and when it was last verified; it does not hype, promise
outcomes, or use exclamation marks. Three words: **authoritative, precise,
current**. Emotional goal: credibility and quiet confidence — the feeling of
consulting a trusted system of record.

## Anti-references

- **Generic AI-generated SaaS landing pages**: centered hero over a gradient
  blob, three identical icon-heading-text cards, geometric sans everywhere,
  gradient text. The single biggest thing to avoid.
- **"We'll connect you to investors!" growth marketplaces** and anything implying
  advisory, coaching, brokerage, matchmaking, or done-for-you services (also a
  payments-compliance failure).
- Crypto/neon-on-black, over-animated hype pages, bounce/elastic motion.
- Hype copy, exclamation marks, outcome promises ("get funded fast").

## Design Principles

1. **The data is the hero.** Show real, structured records (fields, verified
   badges, timestamps) rather than abstract illustrations. The product proves
   itself by looking like authoritative data.
2. **Speak as a record, not a salesperson.** Factual, dated, verified. Editorial
   restraint over persuasion.
3. **Self-serve, never a middleman.** Language and UI emphasize that the user does
   the searching, shortlisting, and outreach. We provide the data and step aside.
4. **Earn trust through precision.** Verified markers, last-sync timestamps,
   consistent fields, exact figures. Trust is the whole product.
5. **Commit to the Ledger.** Type, hairline rules, and structure do the work;
   avoid SaaS decoration and clichés. A clear, opinionated identity beats a safe,
   generic one.

## Accessibility & Inclusion

Target WCAG 2.1 AA. Maintain AA contrast on warm paper/ink and on the dark CTA
band. Never rely on color alone (verified state pairs a ● glyph + text label;
locked contact pairs a 🔒 + "Unlock"). Respect `prefers-reduced-motion` (motion
is enhancement only). Fully keyboard-navigable; semantic, server-rendered HTML
(consistent with the SSR/SEO direction in `docs/phase-2-planning-brief.md`).
