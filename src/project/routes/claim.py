"""Claiming blueprint — Phase 2d Task 4 + Phase 5 Task 2.

Person claim flows: /investor/<slug>/claim* (unchanged)
Organization claim flows: /firm/<slug>/claim* (new)
Shared logic factored through _EntityInfo + _resolve_entity().
"""

from __future__ import annotations

from typing import NamedTuple

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    ClaimRequest,
    ClaimVerification,
    User,
)
from ..models.entity import Organization, Person
from ..utils.cap import verify_captcha
from ..utils.email.resend_client import send_email
from ..utils.enums import EntityType, Status, StatusType
from ..utils.errors.error_messages import (
    CLAIM_REQUEST_ALREADY_SUBMITTED,
    EXPIRED_CODE,
    INVALID_CODE,
    INVESTOR_ALREADY_CLAIMED,
)

claim = Blueprint("claim", __name__)


# ---------------------------------------------------------------------------
# Shared entity resolution helper
# ---------------------------------------------------------------------------


class _EntityInfo(NamedTuple):
    """Resolved entity for either a Person or Organization."""

    entity: Person | Organization
    entity_type: EntityType
    display_name: str
    email: str | None
    slug: str
    profile_url_kwargs: dict  # kwargs for url_for() to redirect after claiming


def _resolve_entity(entity_type: EntityType, slug: str) -> _EntityInfo | None:
    """Look up the entity by slug. Returns None if not found."""
    if entity_type == EntityType.PERSON:
        person = Person.get_by_slug(slug)
        if person is None:
            return None
        return _EntityInfo(
            entity=person,
            entity_type=EntityType.PERSON,
            display_name=person.full_name,
            email=person.email,
            slug=slug,
            profile_url_kwargs={"endpoint": "main.investor_slug", "slug": slug},
        )
    else:
        org = Organization.get_by_slug(slug)
        if org is None:
            return None
        return _EntityInfo(
            entity=org,
            entity_type=EntityType.ORG,
            display_name=org.name,
            email=org.email,
            slug=slug,
            profile_url_kwargs={"endpoint": "public.firm_profile", "path": slug},
        )


def _redirect_to_profile(info: _EntityInfo, **status_kwargs):
    """Build a redirect response to the entity's public profile page."""
    kwargs = dict(info.profile_url_kwargs)
    endpoint = kwargs.pop("endpoint")
    return redirect(url_for(endpoint, _external=False, **kwargs, **status_kwargs))


# ---------------------------------------------------------------------------
# Legacy slug routes — redirect to current search
# ---------------------------------------------------------------------------


@claim.get("/investor/<slug>/claim")
@login_required
def types_view(slug):
    person = Person.get_by_slug(slug)
    if not person:
        return redirect(url_for("public.investors"))

    return render_template("claiming/index.html", investor=person, entity=person, entity_type="person")


@claim.get("/investor/<slug>/claim/manual")
@login_required
def manual_view(slug):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    person = Person.get_by_slug(slug)
    if not person:
        return redirect(url_for("public.investors"))

    return render_template(
        "claiming/manual.html",
        investor=person,
        entity=person,
        entity_type="person",
        status_type=status_type,
        msg=msg,
    )


@claim.post("/investor/<slug>/claim/manual")
@login_required
def manual(slug):
    form_data = request.get_json()
    email = form_data.get("email")

    # Cap captcha verify (skipped automatically when _CAP_* vars are absent).
    cap_token = form_data.get("cap-token") or form_data.get("cap_token")
    if not verify_captcha(cap_token):
        status = Status(StatusType.ERROR, "Captcha verification failed. Please try again.").get_status()
        return redirect(url_for("claim.manual_view", slug=slug, _external=False, **status))

    existing_claim = Person.get_by_user_id(current_user.id)
    if existing_claim:
        status = Status(StatusType.ERROR, "You can't claim another investor account!").get_status()
        return redirect(url_for("claim.manual_view", slug=slug, _external=False, **status))

    person = Person.get_by_slug(slug)
    if not person:
        return jsonify({"status": "error", "message": "Investor not found."}), 404

    claim_request = ClaimRequest.get_by_user_id(current_user.id)
    if claim_request:
        if claim_request.status.value == "pending":
            status = Status(StatusType.ERROR, CLAIM_REQUEST_ALREADY_SUBMITTED).get_status()
            return redirect(url_for("claim.manual_view", slug=slug, _external=False, **status))
        elif claim_request.status.value == "approved":
            status = Status(StatusType.ERROR, INVESTOR_ALREADY_CLAIMED).get_status()
            return redirect(url_for("claim.manual_view", slug=slug, _external=False, **status))

    claim_request = ClaimRequest(
        user_id=current_user.id,
        entity_type=EntityType.PERSON,
        entity_id=person.id,
        email=email,
    )
    db.session.add(claim_request)
    db.session.commit()

    status = Status(StatusType.SUCCESS, "Claim request submitted.").get_status()
    return redirect(url_for("main.investor_slug", slug=slug, _external=False, **status))


@claim.get("/investor/<slug>/claim/email")
@login_required
def email_view(slug):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    person = Person.get_by_slug(slug)
    if not person:
        return redirect(url_for("public.investors"))

    return render_template(
        "claiming/email.html",
        investor=person,
        entity=person,
        entity_type="person",
        status_type=status_type,
        msg=msg,
    )


@claim.post("/investor/<slug>/claim/email")
@login_required
def email(slug):
    form_data = request.get_json() or {}

    # Cap captcha verify (skipped automatically when _CAP_* vars are absent).
    cap_token = form_data.get("cap-token") or form_data.get("cap_token")
    if not verify_captcha(cap_token):
        status = Status(StatusType.ERROR, "Captcha verification failed. Please try again.").get_status()
        return redirect(url_for("claim.email_view", slug=slug, _external=False, **status))

    person = Person.get_by_slug(slug)
    if not person or person.user_id:
        return redirect(url_for("public.investors"))

    # Guard: no email on file for this profile — send user to manual review instead.
    if not person.email:
        status = Status(
            StatusType.ERROR,
            "There is no email on file for this profile. Please use the manual review option.",
        ).get_status()
        return redirect(url_for("claim.manual_view", slug=slug, _external=False, **status))

    existing_claim = Person.get_by_user_id(current_user.id)
    if existing_claim:
        status = Status(StatusType.ERROR, "You can't claim another investor account!").get_status()
        return redirect(url_for("claim.email_view", slug=slug, _external=False, **status))

    verification = ClaimVerification(
        user_id=current_user.id,
        entity_type=EntityType.PERSON,
        entity_id=person.id,
    )
    db.session.add(verification)
    db.session.commit()

    link = url_for("claim.verification_view", slug=slug, verification_code=verification.token, _external=True)
    html = render_template(
        "email/claim_verification.html",
        name=person.full_name,
        link=link,
        token=verification.token,
    )
    send_email(person.email, "Verify your Globalify profile claim", html)

    status = Status(StatusType.SUCCESS, "Verification email sent.").get_status()
    return redirect(url_for("main.investor_slug", slug=slug, _external=False, **status))


@claim.get("/investor/<slug>/claim/email/verify")
@login_required
def verification_view(slug):
    verification_code = request.args.get("verification_code")

    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    person = Person.get_by_slug(slug)
    if not person:
        return redirect(url_for("public.investors"))

    return render_template(
        "claiming/email_verification.html",
        investor=person,
        entity=person,
        entity_type="person",
        verification_code=verification_code,
        status_type=status_type,
        msg=msg,
    )


@claim.post("/investor/<slug>/claim/email/verify")
@login_required
def verification(slug):
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    form_data = request.get_json()
    verification_code = form_data.get("code")

    person = Person.get_by_slug(slug)
    if not person:
        return redirect(url_for("public.investors"))

    # Guard: profile already claimed by someone.
    if person.user_id:
        status = Status(StatusType.ERROR, INVESTOR_ALREADY_CLAIMED).get_status()
        return redirect(url_for("claim.verification_view", slug=slug, _external=False, **status))

    claim_verification = ClaimVerification.get_by_token(verification_code)
    if not claim_verification:
        status = Status(StatusType.ERROR, INVALID_CODE).get_status()
        return redirect(url_for("claim.verification_view", slug=slug, _external=False, **status))

    if claim_verification.is_expired:
        status = Status(StatusType.ERROR, EXPIRED_CODE).get_status()
        return redirect(url_for("claim.verification_view", slug=slug, _external=False, **status))

    if claim_verification.is_used:
        status = Status(StatusType.ERROR, INVALID_CODE).get_status()
        return redirect(url_for("claim.verification_view", slug=slug, _external=False, **status))

    # NOTE: we intentionally do NOT check user_email == current_user.email here.
    # Possession of the token is the proof of identity — the email address check
    # is redundant and breaks legitimate claim flows (e.g. user changed email,
    # or person's on-file email differs from the logged-in account's email).

    person.user_id = current_user.id
    claim_verification.is_used = True

    if not current_user.user_info.first_name:
        current_user.user_info.first_name = person.first_name
    if not current_user.user_info.last_name:
        current_user.user_info.last_name = person.last_name
    if not current_user.user_info.username:
        current_user.user_info.set_username()
    if not current_user.user_info.is_complete:
        current_user.user_info.is_complete = True

    db.session.commit()

    status = Status(StatusType.SUCCESS, "Investor claimed.").get_status()
    return redirect(url_for("main.investor_slug", slug=slug, _external=False, **status))


# ---------------------------------------------------------------------------
# Firm (Organization) claim routes
# ---------------------------------------------------------------------------


@claim.get("/firm/<slug>/claim")
@login_required
def firm_types_view(slug):
    org = Organization.get_by_slug(slug)
    if not org:
        return redirect(url_for("public.firms"))

    return render_template(
        "claiming/index.html",
        investor=org,
        entity=org,
        entity_type="org",
        claim_manual_url=url_for("claim.firm_manual_view", slug=slug),
        claim_email_url=url_for("claim.firm_email_view", slug=slug) if org.email else None,
    )


@claim.get("/firm/<slug>/claim/manual")
@login_required
def firm_manual_view(slug):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    org = Organization.get_by_slug(slug)
    if not org:
        return redirect(url_for("public.firms"))

    return render_template(
        "claiming/manual.html",
        investor=org,
        entity=org,
        entity_type="org",
        status_type=status_type,
        msg=msg,
    )


@claim.post("/firm/<slug>/claim/manual")
@login_required
def firm_manual(slug):
    form_data = request.get_json()
    email = form_data.get("email")

    cap_token = form_data.get("cap-token") or form_data.get("cap_token")
    if not verify_captcha(cap_token):
        status = Status(StatusType.ERROR, "Captcha verification failed. Please try again.").get_status()
        return redirect(url_for("claim.firm_manual_view", slug=slug, _external=False, **status))

    existing_claim = Organization.get_by_user_id(current_user.id)
    if existing_claim:
        status = Status(StatusType.ERROR, "You can't claim another organization account!").get_status()
        return redirect(url_for("claim.firm_manual_view", slug=slug, _external=False, **status))

    org = Organization.get_by_slug(slug)
    if not org:
        return jsonify({"status": "error", "message": "Organization not found."}), 404

    claim_request = ClaimRequest.get_by_user_id(current_user.id)
    if claim_request:
        if claim_request.status.value == "pending":
            status = Status(StatusType.ERROR, CLAIM_REQUEST_ALREADY_SUBMITTED).get_status()
            return redirect(url_for("claim.firm_manual_view", slug=slug, _external=False, **status))
        elif claim_request.status.value == "approved":
            status = Status(StatusType.ERROR, INVESTOR_ALREADY_CLAIMED).get_status()
            return redirect(url_for("claim.firm_manual_view", slug=slug, _external=False, **status))

    claim_request = ClaimRequest(
        user_id=current_user.id,
        entity_type=EntityType.ORG,
        entity_id=org.id,
        email=email,
    )
    db.session.add(claim_request)
    db.session.commit()

    status = Status(StatusType.SUCCESS, "Claim request submitted.").get_status()
    return redirect(url_for("public.firm_profile", path=slug, _external=False, **status))


@claim.get("/firm/<slug>/claim/email")
@login_required
def firm_email_view(slug):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    org = Organization.get_by_slug(slug)
    if not org:
        return redirect(url_for("public.firms"))

    return render_template(
        "claiming/email.html",
        investor=org,
        entity=org,
        entity_type="org",
        status_type=status_type,
        msg=msg,
    )


@claim.post("/firm/<slug>/claim/email")
@login_required
def firm_email(slug):
    form_data = request.get_json() or {}

    cap_token = form_data.get("cap-token") or form_data.get("cap_token")
    if not verify_captcha(cap_token):
        status = Status(StatusType.ERROR, "Captcha verification failed. Please try again.").get_status()
        return redirect(url_for("claim.firm_email_view", slug=slug, _external=False, **status))

    org = Organization.get_by_slug(slug)
    if not org or org.user_id:
        return redirect(url_for("public.firms"))

    if not org.email:
        status = Status(
            StatusType.ERROR,
            "There is no email on file for this profile. Please use the manual review option.",
        ).get_status()
        return redirect(url_for("claim.firm_manual_view", slug=slug, _external=False, **status))

    existing_claim = Organization.get_by_user_id(current_user.id)
    if existing_claim:
        status = Status(StatusType.ERROR, "You can't claim another organization account!").get_status()
        return redirect(url_for("claim.firm_email_view", slug=slug, _external=False, **status))

    verification = ClaimVerification(
        user_id=current_user.id,
        entity_type=EntityType.ORG,
        entity_id=org.id,
    )
    db.session.add(verification)
    db.session.commit()

    link = url_for("claim.firm_verification_view", slug=slug, verification_code=verification.token, _external=True)
    html = render_template(
        "email/claim_verification.html",
        name=org.name,
        link=link,
        token=verification.token,
    )
    send_email(org.email, "Verify your Globalify profile claim", html)

    status = Status(StatusType.SUCCESS, "Verification email sent.").get_status()
    return redirect(url_for("public.firm_profile", path=slug, _external=False, **status))


@claim.get("/firm/<slug>/claim/email/verify")
@login_required
def firm_verification_view(slug):
    verification_code = request.args.get("verification_code")

    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    org = Organization.get_by_slug(slug)
    if not org:
        return redirect(url_for("public.firms"))

    return render_template(
        "claiming/email_verification.html",
        investor=org,
        entity=org,
        entity_type="org",
        verification_code=verification_code,
        status_type=status_type,
        msg=msg,
    )


@claim.post("/firm/<slug>/claim/email/verify")
@login_required
def firm_verification(slug):
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    form_data = request.get_json()
    verification_code = form_data.get("code")

    org = Organization.get_by_slug(slug)
    if not org:
        return redirect(url_for("public.firms"))

    if org.user_id:
        status = Status(StatusType.ERROR, INVESTOR_ALREADY_CLAIMED).get_status()
        return redirect(url_for("claim.firm_verification_view", slug=slug, _external=False, **status))

    claim_verification = ClaimVerification.get_by_token(verification_code)
    if not claim_verification:
        status = Status(StatusType.ERROR, INVALID_CODE).get_status()
        return redirect(url_for("claim.firm_verification_view", slug=slug, _external=False, **status))

    if claim_verification.is_expired:
        status = Status(StatusType.ERROR, EXPIRED_CODE).get_status()
        return redirect(url_for("claim.firm_verification_view", slug=slug, _external=False, **status))

    if claim_verification.is_used:
        status = Status(StatusType.ERROR, INVALID_CODE).get_status()
        return redirect(url_for("claim.firm_verification_view", slug=slug, _external=False, **status))

    org.user_id = current_user.id
    claim_verification.is_used = True

    if not current_user.user_info.first_name:
        current_user.user_info.first_name = org.name
    if not current_user.user_info.username:
        current_user.user_info.set_username()
    if not current_user.user_info.is_complete:
        current_user.user_info.is_complete = True

    db.session.commit()

    status = Status(StatusType.SUCCESS, "Organization claimed.").get_status()
    return redirect(url_for("public.firm_profile", path=slug, _external=False, **status))
