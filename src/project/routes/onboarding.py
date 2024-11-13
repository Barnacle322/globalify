import re

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
)
from sqlalchemy import select

from ..extensions import db
from ..models import (
    ClaimRequest,
    Country,
    EmailVerification,
    Industry,
    Investor,
    NotableInvestment,
    Notification,
    Round,
    User,
    UserInfo,
)
from ..utils.enums import Events, OauthProvider, Status, StatusType
from ..utils.errors.error_messages import (
    AUTH_FIELDS_INCOMPLETE,
    AUTH_USERNAME_USED,
)
from ..utils.google_helpers import google_pubsub

onboarding = Blueprint("onboarding", __name__)


@onboarding.route("/", methods=["GET"])
@login_required
def index():
    if current_user.is_authenticated and current_user.user_info.is_complete:
        return redirect(url_for("main.search"))

    claim_requests = ClaimRequest.get_with_investor_by_user_id(current_user.id)

    last_claim_request = claim_requests[0] if claim_requests else None

    return render_template(
        "onboarding/index.html", claim_requests=claim_requests, last_claim_request=last_claim_request
    )


@onboarding.route("/basic", methods=["GET", "POST"])
@login_required
def basic():
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    user_info = UserInfo.get_by_user_id(current_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    if user_info.is_complete:
        return redirect(url_for("main.search"))

    if request.method == "POST":
        f = request.form
        first_name, last_name, username = f.get("first_name"), f.get("last_name"), f.get("username")

        if not first_name or not last_name or not username:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(
                url_for(
                    "onboarding.basic",
                    next=request.args.get("next"),
                    _external=False,
                    **status,
                )
            )

        if UserInfo.is_taken(username):
            status = Status(StatusType.ERROR, AUTH_USERNAME_USED).get_status()
            return redirect(
                url_for(
                    "onboarding.basic",
                    next=request.args.get("next"),
                    _external=False,
                    **status,
                )
            )

        if not re.match(r"^[a-zA-Z0-9]{4,20}$", username) and username != "None":
            status = Status(
                StatusType.ERROR, "Username must be between 4 and 20 characters and contain only letters and numbers"
            ).get_status()
            return redirect(
                url_for(
                    "onboarding.basic",
                    next=request.args.get("next"),
                    _external=False,
                    **status,
                )
            )

        user_info.first_name = first_name
        user_info.last_name = last_name
        user_info.username = username.lower()
        user_info.is_complete = True
        db.session.commit()

        if current_user.oauth_provider == OauthProvider.GOOGLE:
            current_user.is_verified = True
            db.session.commit()
        elif not current_user.is_verified:
            verification = EmailVerification(user_id=current_user.id)
            db.session.add(verification)
            db.session.commit()

            google_pubsub.send_event(
                "A new user has completed onboarding!",
                email=current_user.email,
                event_type=Events.USER_COMPLETED_ONBOARDING.value,
                random_key=verification.token,
            )

        return redirect(url_for("main.search", next=request.args.get("next")))

    return render_template(
        "onboarding/basic.html",
        user_info=user_info.sanitize(),
        status_type=request.args.get("type"),
        msg=request.args.get("msg"),
    )


@onboarding.route("/investor", methods=["GET", "POST"])
@login_required
def investor():
    if not current_user or not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    if current_user.user_info.is_complete:
        return redirect(url_for("auth.login"))

    claim_request = ClaimRequest.get_by_user_id(current_user.id)
    if claim_request:
        if claim_request.status.value == "pending":
            return redirect(url_for("onboarding.index"))

    if request.method == "POST":
        form_data = request.get_json()

        first_name = form_data.get("firstName")
        if not first_name:
            return jsonify({"error": "First name is required"}), 400

        last_name = form_data.get("lastName")
        if not last_name:
            return jsonify({"error": "Last name is required"}), 400

        email = form_data.get("email") or None
        if email:
            existing_investor_by_email = Investor.get_by_email(email)
            if existing_investor_by_email:
                return jsonify({"error": "Email is already in use"}), 400

        investor = Investor(
            user_id=current_user.id,
            first_name=first_name,
            last_name=last_name,
            slug=form_data.get("slug") or None,
            firm_name=form_data.get("firmName") or None,
            position=form_data.get("position") or None,
            about=form_data.get("about") or None,
            location=form_data.get("location") or None,
            n_investments=int(form_data.get("nInvestments") or 0),
            n_exits=int(form_data.get("nIxits") or 0),
            min_investment=int(form_data.get("minInvestment") or 0),
            max_investment=int(form_data.get("maxInvestment") or 0),
            website=form_data.get("website") or None,
            linkedin=form_data.get("linkedin") or None,
            twitter=form_data.get("twitter") or None,
            email=email,
            phone_number=form_data.get("phoneNumber") or None,
            rounds=list(Round.get_by_id_list(form_data.get("selectedRounds") or [])),
            industries=list(Industry.get_by_id_list(form_data.get("selectedIndustries") or [""])),
            notable_investments=list(
                NotableInvestment.get_by_id_list(form_data.get("selectedNotableInvestments") or [])
            ),
        )

        try:
            db.session.add(investor)
            db.session.commit()
        except Exception:
            return redirect(url_for("onboarding.index"))

        investor.set_slug()

        try:
            investor.upsert_data()
        except Exception:
            return redirect(url_for("onboarding.index"))

        current_user.user_info.is_complete = True
        current_user.user_info.first_name = first_name
        current_user.user_info.last_name = last_name
        current_user.user_info.set_username()

        if current_user.oauth_provider == OauthProvider.GOOGLE:
            current_user.is_verified = True
            db.session.commit()
        elif not current_user.is_verified:
            verification = EmailVerification(user_id=current_user.id)
            db.session.add(verification)
            db.session.commit()

            google_pubsub.send_event(
                "A new user has completed onboarding!",
                email=current_user.email,
                event_type=Events.USER_COMPLETED_ONBOARDING.value,
                random_key=verification.token,
            )

        notification = Notification(
            user=current_user,
            json_data={
                "title": "Info",
                "msg": "Welcome to our platform. You have successfully completed registration. Explore the world of investment with us!",
                "type": "system",
                "item": {"type": "info", "url": "/search"},
            },
        )
        db.session.add(notification)
        db.session.commit()

        return redirect(url_for("main.search"))

    return render_template(
        "onboarding/investor.html",
        user=current_user,
        countries=Country.get_all(),
        industries=Industry.get_all(),
        rounds=Round.get_all(),
    )


@onboarding.get("/check-investor/<email>")
def check_investor(email):
    existing_investor_by_email = Investor.get_by_email(email)
    return jsonify({"investor_exists": bool(existing_investor_by_email)})


@onboarding.get("/search_notable_investments/<search_input>")
def search_notable_investment(search_input):
    notable_investments = db.session.scalars(
        select(NotableInvestment)
        .where(NotableInvestment.name.contains(search_input))
        .where(NotableInvestment.company_id.is_(None))
    ).all()

    return jsonify(notable_investments=[ni.to_dict() for ni in notable_investments])
