import re

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
)

from ..extensions import db
from ..models import (
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
from ..schemas.notification import NotificationLayout
from ..utils.enums import (
    Events,
    NotificationDestination,
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

    notifications = Notification.get_unread(
        user_id=authenticated_user.id,
        destination=NotificationDestination.ONBOARDING,
    )

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
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(title="Error!", msg=AUTH_FIELDS_INCOMPLETE).model_dump(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("onboarding.index"))

        if UserInfo.is_taken(username):
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(title="Error!", msg=AUTH_USERNAME_USED).model_dump(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("onboarding.index"))

        if not re.match(r"^[a-zA-Z0-9]{4,20}$", username) and username != "None":
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(
                    title="Incorrect format!",
                    msg="Username must be between 4 and 20 characters and can only contain letters and numbers",
                ).model_dump(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("onboarding.index"))

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

    return render_template("onboarding/basic.html", user_info=user_info.sanitize(), notifications=notifications)


@onboarding.route("/investor", methods=["GET", "POST"])
@login_required
def investor():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    notifications = Notification.get_unread(
        user_id=authenticated_user.id,
        destination=NotificationDestination.ONBOARDING,
    )

    countries = Country.get_all()
    industries = Industry.get_all()

    print("\n\n\n\n\n\n\n\n\n\n\n\n")
    print(industries)

    rounds = Round.get_all()
    notable_investments = NotableInvestment.get_all()

    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        form_data = request.get_json()

        first_name = form_data.get("first_name")
        last_name = form_data.get("last_name")
        slug = form_data.get("slug") or None
        firm_name = form_data.get("firm_name") or None
        position = form_data.get("position") or None
        about = form_data.get("about") or None
        location = form_data.get("location") or None

        n_investments = int(form_data.get("n_investments") or 0)
        n_exits = int(form_data.get("n_exits") or 0)
        min_investment = int(form_data.get("min_investment") or 0)
        max_investment = int(form_data.get("max_investment") or 0)

        selected_round_ids = form_data.get("selectedRounds") or []
        selected_industry_ids = form_data.get("selectedIndustries") or [""]
        selected_notable_investment_ids = form_data.get("selectedNotableInvestments") or []

        website = form_data.get("website") or None
        linkedin = form_data.get("linkedin") or None
        twitter = form_data.get("twitter") or None
        email = form_data.get("email") or None
        phone_number = form_data.get("phone_number") or None

        if not first_name:
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(title="Error!", msg=AUTH_FIELDS_INCOMPLETE).model_dump(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("onboarding.index"))

        if email:
            existing_email = Investor.get_by_email(email)
            if existing_email:
                notification = Notification(
                    user=authenticated_user,
                    json_data=NotificationLayout(title="Error!", msg="Email already in use").model_dump(),
                    destination=NotificationDestination.ONBOARDING,
                )
                db.session.add(notification)
                db.session.commit()
                return redirect(url_for("onboarding.index"))

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
        except Exception as e:
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(title="Error!", msg=f"{e}").model_dump(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("onboarding.index"))

        investor.set_slug()

        try:
            investor.upsert_data()
        except Exception as e:
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(title="Error!", msg=f"{e}").model_dump(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("onboarding.index"))

        return redirect(url_for("main.search"))

    return render_template(
        "onboarding/investor.html",
        user_info=user_info.sanitize(),
        notifications=notifications,
        countries=countries,
        industries=industries,
        rounds=rounds,
        # notable_investments=notable_investments,
    )
