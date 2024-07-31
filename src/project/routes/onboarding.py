import re

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
)

from ..extensions import db
from ..models import (
    EmailVerification,
    Notification,
    User,
    UserInfo,
)
from ..utils.enums import (
    NotificationDestination,
    NotificationLayout,
)
from ..utils.errors.error_messages import (
    AUTH_FIELDS_INCOMPLETE,
    AUTH_USERNAME_USED,
)

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
        is_read=False,
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
                json_data=NotificationLayout(title="Error!", msg=AUTH_FIELDS_INCOMPLETE).get_json(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("onboarding.index"))

        if UserInfo.is_taken(username):
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(title="Error!", msg=AUTH_USERNAME_USED).get_json(),
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
                ).get_json(),
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

        if not authenticated_user.is_verified:
            verification = EmailVerification(user_id=authenticated_user.id)
            db.session.add(verification)
            db.session.commit()
            # TODO
            # google_pubsub.send_event(
            #     "A new user has completed onboarding!",
            #     email=authenticated_user.email,
            #     event_type=Events.USER_COMPLETED_ONBOARDING.value,
            #     random_key=verification.token,
            # )

        return redirect(url_for("main.search", next=next_url))

    return render_template("onboarding/basic.html", user_info=user_info.sanitize(), notifications=notifications)


@onboarding.route("/investor", methods=["GET", "POST"])
@login_required
def investor():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    notifications = Notification.get_unread(
        user_id=authenticated_user.id,
        destination=NotificationDestination.ONBOARDING,
        is_read=False,
    )

    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    return render_template("onboarding/investor.html", user_info=user_info.sanitize(), notifications=notifications)
