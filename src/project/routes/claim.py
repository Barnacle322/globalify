"""Claiming blueprint — Phase 2d Task 4.

Legacy claim flows (dependent on removed ORM models) have been replaced with
entity-model paths using Person / ClaimRequest.  Legacy URL shapes are kept
so that existing bookmarked links return sensible responses.
"""

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
from ..models.entity import Person
from ..utils.cap import verify_captcha
from ..utils.enums import Status, StatusType
from ..utils.errors.error_messages import (
    CLAIM_REQUEST_ALREADY_SUBMITTED,
    EXPIRED_CODE,
    INVALID_CODE,
    INVALID_EMAIL,
    INVESTOR_ALREADY_CLAIMED,
)

claim = Blueprint("claim", __name__)


# ---------------------------------------------------------------------------
# Legacy slug routes — redirect to current search
# ---------------------------------------------------------------------------


@claim.get("/investor/<slug>/claim")
@login_required
def types_view(slug):
    person = Person.get_by_slug(slug)
    if not person:
        return redirect(url_for("public.investors"))

    return render_template("claiming/index.html", investor=person)


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

    from ..utils.enums import EntityType

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

    return render_template("claiming/email.html", investor=person, status_type=status_type, msg=msg)


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

    existing_claim = Person.get_by_user_id(current_user.id)
    if existing_claim:
        status = Status(StatusType.ERROR, "You can't claim another investor account!").get_status()
        return redirect(url_for("claim.email_view", slug=slug, _external=False, **status))

    from ..utils.enums import EntityType

    verification = ClaimVerification(
        user_id=current_user.id,
        entity_type=EntityType.PERSON,
        entity_id=person.id,
    )
    db.session.add(verification)
    db.session.commit()

    # TODO Phase 3: send claim verification email via magic-link service

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
    user_email = form_data.get("email")

    person = Person.get_by_slug(slug)
    if not person:
        return redirect(url_for("public.investors"))

    claim_verification = ClaimVerification.get_by_token(verification_code)
    if not claim_verification:
        status = Status(StatusType.ERROR, INVALID_CODE).get_status()
        return redirect(url_for("claim.verification_view", slug=slug, _external=False, **status))

    if claim_verification.is_expired:
        status = Status(StatusType.ERROR, EXPIRED_CODE).get_status()
        return redirect(url_for("claim.verification_view", slug=slug, _external=False, **status))

    if user_email != current_user.email:
        status = Status(StatusType.ERROR, INVALID_EMAIL).get_status()
        return redirect(url_for("claim.verification_view", slug=slug, _external=False, **status))

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
