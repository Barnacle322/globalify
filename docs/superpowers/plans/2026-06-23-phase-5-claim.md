# Phase 5 — Claim-Your-Profile (finish the rework onto Person/Org)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`).

**Goal:** Complete the claim flow on the new model — actually SEND the verification email (via Resend), fix the `is_expired`-property bug, extend claiming to Organizations (not just Person), and add the public "Claim this profile" CTA + a verified badge on claimed profiles. The growth/freshness/SEO loop the directory depends on.

**Architecture:** Two claim paths already exist on the entity model (`claim.py`): **email-token** (a `ClaimVerification` token mailed to the entity's ON-FILE email — controlling that inbox proves the claim) and **manual** (Cap + a `ClaimRequest` for admin review). The infra is in place — Cap verify (Phase 3), Resend email (Phase 3), magic-link auth (Phase 2e), the admin `edit_claim_request` → `Person.user_id` binding (Phase 2d). This phase fills the gaps. Design reference: master spec **§1 (claiming journey), §6**.

## Global Constraints

- **Branch:** `revamp/pivot-design`. Never `main`.
- **Email-token path semantics:** the verification link/code goes to the ENTITY's on-file email (`person.email`/`org.email`), NOT the logged-in user's email — controlling that inbox is the proof. Send via the Phase 3 `send_email` (Resend if configured, else the log stub). Token is single-use + expiring (the model already has this; reuse).
- **Both entity types:** claiming must work for `Person` (investors) AND `Organization` (firms). If `Organization` lacks a `user_id` (claimed-by), add it + a migration.
- **Cap stays wired** on the claim submit (Phase 3). Magic-link is the auth (a claimer logs in via magic-link first; claim routes are `@login_required`).
- **Verification gate (every task):** `FLASK_ENV=testing SECRET_KEY=x uv run pytest` green; `uv run ruff check . && uv run ruff format --check .` clean (note: ruff `target-version` is `py313` now — keep `except (A, B):` parenthesized); app imports + `db.create_all`. Playwright where stated.
- **Commits:** conventional subject; trailer `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`.

---

## Task 1: Send the verification email (Resend) + fix the `is_expired` bug + tidy verify

**Files:** `src/project/routes/claim.py` (the `email`/`verification` handlers), `src/project/models/claim.py` (`ClaimVerification.expire_all_by_user_id`), a claim email template `templates/email/claim_verification.html`, `tests/test_claim.py`.

- [ ] **Step 1:** Fix `ClaimVerification.expire_all_by_user_id` (`models/claim.py`): it sets `claim_verification.is_expired = True`, but `is_expired` is a read-only `@property` → set `is_used = True` instead (mark consumed). (Same bug pattern fixed for `EmailVerification` in Phase 1a.)
- [ ] **Step 2:** Fill the email-send TODO in `claim.py`'s `email(slug)` handler: after creating the `ClaimVerification`, build the verification URL (`url_for("claim.verification_view", slug=slug, verification_code=verification.token, _external=True)`), render `templates/email/claim_verification.html` (extends the `email/_layout.html` from Phase 3; shows the entity name + the verify link/code), and `send_email(<entity on-file email>, "Verify your Globalify profile claim", html)` — to the ENTITY's email (`person.email`), NOT `current_user.email`. If the entity has no on-file email, surface a friendly "no email on file — use manual review" message instead. (Send is gated by Resend config; logs in dev.)
- [ ] **Step 3:** Tidy the `verification` POST: the proof is possessing the token from the entity's-email link. Keep the single-use + expiry checks (`get_by_token`, `is_expired`, `is_used`). On success bind `person.user_id = current_user.id`, mark `is_used=True`, copy name into `user_info` (as it does), commit. Drop or relax the `user_email != current_user.email` check (that conflated the logged-in user with the entity's email — the email path's proof is the token, not matching the logged-in email; document the decision). Guard against re-claiming an already-claimed entity (`person.user_id` already set).
- [ ] **Step 4:** `tests/test_claim.py`: email path — POST `/investor/<slug>/claim/email` creates a `ClaimVerification` AND calls `send_email` (monkeypatch/caplog) to the PERSON's email; the verify POST with the right token binds `person.user_id` + marks the token used; expired token rejected; already-used token rejected; a second claim of an already-claimed person rejected; `expire_all_by_user_id` sets `is_used` (not the property). Reuse the auth-fixture pattern. Write tests first, run (fail), implement, green.
- [ ] **Step 5: Gate. Commit** (`feat(claim): send verification email via Resend; fix is_expired bug; harden verify`).

---

## Task 2: Claim Organizations + "Claim this profile" CTA + verified badge

**Files:** `models/entity.py` (`Organization.user_id` if missing) + Alembic, `routes/claim.py` (firm claim routes / generalize), `templates/profiles/person.html` + `organization.html` (CTA + badge), the `claiming/*` templates (org support), `tests/test_claim.py` + Playwright.

- [ ] **Step 1:** If `Organization` has no `user_id` (claimed-by) column, add `user_id: Mapped[int | None]` FK `user.id` + an Alembic revision (chain off head) + an `Organization.get_by_user_id`. (Mirror `Person.user_id`.)
- [ ] **Step 2:** Generalize the claim routes for firms: add `/firm/<slug>/claim`, `/firm/<slug>/claim/email`, `/firm/<slug>/claim/email/verify`, `/firm/<slug>/claim/manual` (mirroring the investor ones) resolving `Organization.get_by_slug` and using `entity_type=EntityType.ORG`, binding `organization.user_id` on success. Factor the shared logic so the two entity types don't duplicate (a helper keyed on entity_type). The `claiming/*` templates take the entity generically (name/slug/email).
- [ ] **Step 3:** Public entry point: on `profiles/person.html` + `organization.html`, add a **"Claim this profile"** CTA (links to the claim entry for that entity) shown ONLY when the entity is unclaimed (`not entity.user_id`) AND for a logged-in user (or a "log in to claim" prompt for anonymous). When claimed, show a **verified badge** ("✓ Claimed / Verified") instead.
- [ ] **Step 4:** Ensure a claimer can edit their claimed profile — the settings/admin edit path is on `Person`/`Organization` (Phase 2d); confirm a claimed user reaches an edit view (link from the profile when `entity.user_id == current_user.id`). Minimal — don't rebuild the editor.
- [ ] **Step 5:** `tests/test_claim.py`: an Organization can be claimed via the firm email path (binds `organization.user_id`); the CTA renders on an unclaimed profile + is absent on a claimed one (render assertion, both person + org); the verified badge shows on a claimed profile.
- [ ] **Step 6: Gate** (pytest green; ruff; import; `npm run build:css`).
- [ ] **Step 7: Playwright** (seed + Docker Typesense): on an unclaimed `/investors/<slug>` and `/firms/<slug>`, the "Claim this profile" CTA renders; on a claimed one (set `user_id` in the seed) the verified badge renders instead; 0 console errors. Screenshot a profile with the badge → `.playwright-mcp/p5-claimed.jpeg`. Tear down.
- [ ] **Step 8: Commit** (`feat(claim): claim Organizations; claim CTA + verified badge on profiles`).

---

## Self-Review

**Coverage:** verification email via Resend + is_expired fix + verify hardening (T1) · Organization claiming + CTA + verified badge (T2). Completes the claim journey (master spec §1).

**Deferred:** claim resend/throttle UX polish (the model has `is_resendable`); claim-driven profile-enrichment beyond name copy (the editor exists from 2d); admin claim-review UI polish (functional from 2d). 

**Risk control:** email-token proof is possession of a token sent to the entity's on-file email (not a self-asserted match); Cap guards the submit; single-use + expiring tokens; re-claim guarded; both entity types share one code path (no drift); CTA/badge are server-rendered. Email send is Resend-gated (logs in dev), so no external dependency to build/test.
