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
    Investor,
    InvestorOriginPoint,
    User,
)
from ..utils.enums import Status, StatusType
from ..utils.errors.error_messages import (
    CLAIM_REQUEST_ALREADY_SUBMITTED,
    EXPIRED_CODE,
    INVALID_CODE,
    INVALID_EMAIL,
    INVESTOR_ALREADY_CLAIMED,
)

claim = Blueprint("claim", __name__)


@claim.get("/investor/<slug>/claim")
@login_required
def types_view(slug):
    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("search.investor_search"))

    if email := investor.email:
        email = email[:3] + "*" * (len(email) - 6) + email[-3:]
        investor.email = email

    return render_template("claiming/index.html", investor=investor)


@claim.get("/investor/<slug>/claim/manual")
@login_required
def manual_view(slug):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("search.investor_search"))

    return render_template(
        "claiming/manual.html",
        investor=investor,
        status_type=status_type,
        msg=msg,
    )


@claim.post("/investor/<slug>/claim/manual")
@login_required
def manual(slug):
    form_data = request.get_json()
    email = form_data.get("email")

    existing_claim = Investor.get_by_user_id(current_user.id)
    if existing_claim:
        status = Status(StatusType.ERROR, "You can't claim another investor account!").get_status()
        return redirect(url_for("claim.manual_view", slug=slug, _external=False, **status))

    investor = Investor.get_by_slug(slug)
    if not investor:
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
        investor_id=investor.id,
        email=email,
    )
    db.session.add(claim_request)

    investor_point_origin = InvestorOriginPoint.get_by_investor_id(investor.id)
    if not investor_point_origin:
        investor_point_origin = InvestorOriginPoint(investor=investor)
        investor_point_origin.first_name = investor.first_name
        investor_point_origin.last_name = investor.last_name
        investor_point_origin.slug = investor.slug
        investor_point_origin.firm_name = investor.firm_name
        investor_point_origin.about = investor.about
        investor_point_origin.position = investor.position
        investor_point_origin.website = investor.website
        investor_point_origin.linkedin = investor.linkedin
        investor_point_origin.twitter = investor.twitter
        investor_point_origin.email = investor.email
        investor_point_origin.phone_number = investor.phone_number
        investor_point_origin.n_investments = investor.n_investments
        investor_point_origin.n_exits = investor.n_exits
        investor_point_origin.min_investment = investor.min_investment
        investor_point_origin.max_investment = investor.max_investment
        investor_point_origin.location = investor.location
        investor_point_origin.notable_investments = investor.notable_investments
        investor_point_origin.rounds = investor.rounds
        investor_point_origin.industries = investor.industries
        db.session.add(investor_point_origin)
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

    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("search.investor_search"))

    return render_template("claiming/email.html", investor=investor, status_type=status_type, msg=msg)


@claim.post("/investor/<slug>/claim/email")
@login_required
def email(slug):
    investor = Investor.get_by_slug(slug)
    if not investor or investor.user_id:
        return redirect(url_for("search.investor_search"))

    existing_claim = Investor.get_by_user_id(current_user.id)
    if existing_claim:
        status = Status(StatusType.ERROR, "You can't claim another investor account!").get_status()
        return redirect(url_for("claim.email_view", slug=slug, _external=False, **status))

    verification = ClaimVerification(user_id=current_user.id, investor_id=investor.id)
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

    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("search.investor_search"))

    return render_template(
        "claiming/email_verification.html",
        investor=investor,
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

    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("search.investor_search"))

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

    investor.user_id = current_user.id
    claim_verification.is_used = True

    if not current_user.user_info.first_name:
        current_user.user_info.first_name = investor.first_name
    if not current_user.user_info.last_name:
        current_user.user_info.last_name = investor.last_name
    if not current_user.user_info.username:
        current_user.user_info.set_username()
    if not current_user.user_info.is_complete:
        current_user.user_info.is_complete = True

    investor_point_origin = InvestorOriginPoint.get_by_investor_id(investor.id)
    if not investor_point_origin:
        investor_point_origin = InvestorOriginPoint(investor=investor)
        investor_point_origin.first_name = investor.first_name
        investor_point_origin.last_name = investor.last_name
        investor_point_origin.slug = investor.slug
        investor_point_origin.firm_name = investor.firm_name
        investor_point_origin.about = investor.about
        investor_point_origin.position = investor.position
        investor_point_origin.website = investor.website
        investor_point_origin.linkedin = investor.linkedin
        investor_point_origin.twitter = investor.twitter
        investor_point_origin.email = investor.email
        investor_point_origin.phone_number = investor.phone_number
        investor_point_origin.n_investments = investor.n_investments
        investor_point_origin.n_exits = investor.n_exits
        investor_point_origin.min_investment = investor.min_investment
        investor_point_origin.max_investment = investor.max_investment
        investor_point_origin.location = investor.location
        investor_point_origin.notable_investments = investor.notable_investments
        investor_point_origin.rounds = investor.rounds
        investor_point_origin.industries = investor.industries
        db.session.add(investor_point_origin)

    db.session.commit()

    status = Status(StatusType.SUCCESS, "Investor claimed.").get_status()
    return redirect(url_for("main.investor_slug", slug=slug, _external=False, **status))
