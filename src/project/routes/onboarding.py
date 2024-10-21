import re

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
)
from sqlalchemy import select

from ..extensions import db
from ..models import (
    Country,
    EmailVerification,
    Industry,
    Investor,
    NotableInvestment,
    Round,
    User,
    UserInfo,
)
from ..utils.enums import (
    Events,
    OauthProvider,
)
from ..utils.errors.error_messages import (
    AUTH_FIELDS_INCOMPLETE,
    AUTH_USERNAME_USED,
)
from ..utils.google_helpers import google_pubsub

onboarding = Blueprint("onboarding", __name__)


@onboarding.route("/", methods=["GET"])
@login_required
def index():
    return render_template("onboarding/index.html")


@onboarding.route("/basic", methods=["GET", "POST"])
@login_required
def basic():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    next_url = request.args.get("next")

    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    if user_info.is_complete:
        return redirect(url_for("main.search"))

    if request.method == "POST":
        f = request.form
        first_name, last_name, username = f.get("first_name"), f.get("last_name"), f.get("username")

        if not first_name or not last_name or not username:
            return jsonify({"error": AUTH_FIELDS_INCOMPLETE}), 400

        if UserInfo.is_taken(username):
            return jsonify({"error": AUTH_USERNAME_USED}), 400

        if not re.match(r"^[a-zA-Z0-9]{4,20}$", username) and username != "None":
            return jsonify(
                {"error": "Username must be between 4 and 20 characters and contain only letters and numbers"}
            ), 400

        user_info.first_name = first_name
        user_info.last_name = last_name
        user_info.username = username.lower()
        user_info.is_complete = True
        db.session.commit()

        if authenticated_user.oauth_provider == OauthProvider.GOOGLE:
            authenticated_user.is_verified = True
            db.session.commit()
        elif not authenticated_user.is_verified:
            verification = EmailVerification(user_id=authenticated_user.id)
            db.session.add(verification)
            db.session.commit()

            google_pubsub.send_event(
                "A new user has completed onboarding!",
                email=authenticated_user.email,
                event_type=Events.USER_COMPLETED_ONBOARDING.value,
                random_key=verification.token,
            )

        return redirect(url_for("main.search", next=next_url))

    return render_template("onboarding/basic.html", user_info=user_info.sanitize())


@onboarding.route("/investor", methods=["GET", "POST"])
@login_required
def investor():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    countries = Country.get_all()
    industries = Industry.get_all()
    rounds = Round.get_all()

    user = User.get_by_id(authenticated_user.id)
    if not user:
        return redirect(url_for("auth.login"))

    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    if user_info.is_complete:
        return redirect(url_for("main.search"))

    if request.method == "POST":
        form_data = request.get_json()

        first_name = form_data.get("firstName")
        last_name = form_data.get("lastName")
        slug = form_data.get("slug") or None
        firm_name = form_data.get("firmName") or None
        position = form_data.get("position") or None
        about = form_data.get("about") or None
        location = form_data.get("location") or None

        n_investments = int(form_data.get("nInvestments") or 0)
        n_exits = int(form_data.get("nIxits") or 0)
        min_investment = int(form_data.get("minInvestment") or 0)
        max_investment = int(form_data.get("maxInvestment") or 0)

        selected_round_ids = form_data.get("selectedRounds") or []
        selected_industry_ids = form_data.get("selectedIndustries") or [""]
        selected_notable_investment_ids = form_data.get("selectedNotableInvestments") or []

        website = form_data.get("website") or None
        linkedin = form_data.get("linkedin") or None
        twitter = form_data.get("twitter") or None
        email = form_data.get("email") or None
        phone_number = form_data.get("phoneNumber") or None

        if not first_name:
            return jsonify({"error": "First name is required"}), 400

        investor = Investor(
            user_id=authenticated_user.id,
            first_name=first_name,
            last_name=last_name,
            slug=slug,
            firm_name=firm_name,
            position=position,
            about=about,
            location=location,
            n_investments=n_investments,
            n_exits=n_exits,
            min_investment=min_investment,
            max_investment=max_investment,
            website=website,
            linkedin=linkedin,
            twitter=twitter,
            email=email,
            phone_number=phone_number,
            rounds=list(Round.get_by_id_list(selected_round_ids)),
            industries=list(Industry.get_by_id_list(selected_industry_ids)),
            notable_investments=list(NotableInvestment.get_by_id_list(selected_notable_investment_ids)),
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

        user_info.is_complete = True
        db.session.commit()

        if authenticated_user.oauth_provider == OauthProvider.GOOGLE:
            authenticated_user.is_verified = True
            db.session.commit()
        elif not authenticated_user.is_verified:
            verification = EmailVerification(user_id=authenticated_user.id)
            db.session.add(verification)
            db.session.commit()

            google_pubsub.send_event(
                "A new user has completed onboarding!",
                email=authenticated_user.email,
                event_type=Events.USER_COMPLETED_ONBOARDING.value,
                random_key=verification.token,
            )

        return redirect(url_for("main.search"))

    return render_template(
        "onboarding/investor.html",
        user=user,
        countries=countries,
        industries=industries,
        rounds=rounds,
    )


@onboarding.get("/search_notable_investments/<search_input>")
def search_notable_investment(search_input):
    notable_investments = (
        db.session.execute(
            select(NotableInvestment)
            .where(NotableInvestment.name.contains(search_input))
            .where(NotableInvestment.company_id.is_(None))
        )
        .scalars()
        .all()
    )

    return jsonify(
        notable_investments=[
            {"id": notable_investment.id, "name": notable_investment.name} for notable_investment in notable_investments
        ]
    )
