import datetime
import os

import requests
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

from ..extensions import db, login_manager, oauth
from ..models import (
    CompanyInvitation,
    EmailVerification,
    Notification,
    User,
    UserCompany,
    UserInfo,
    UserPayment,
)
from ..schemas.notification import NotificationItem, NotificationLayout
from ..utils.enums import (
    Events,
    NotificationDestination,
    OauthProvider,
    Status,
    StatusType,
)
from ..utils.errors.error_messages import (
    ACCOUNT_NOT_FOUND,
    OAUTH_ACCESS_TOKEN,
    OAUTH_COULD_NOT_RETRIEVE_DATA,
    OAUTH_MISMATCHED_PROVIDER,
    OAUTH_NO_EMAIL,
    OAUTH_NO_USER_INFO,
)
from ..utils.google_helpers import google_pubsub
from .main import check_user_info_complete, check_verification

auth = Blueprint("auth", __name__)

LINKEDIN_SECRET = os.environ.get("_LINKEDIN_OAUTH2_CLIENT_SECRET")
LINKEDIN_EMAIL_URL = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
LINKEDIN_PERSONAL_INFO_URL = "https://api.linkedin.com/v2/me"


@login_manager.user_loader
def load_user(user_id: int) -> User | None:
    user = User.get_by_id(id=int(user_id))
    if user:
        return user
    return None


def oauth_user(email: str, oauth_provider: OauthProvider) -> User:
    user = User.get_by_email(email)
    if not user:
        user = User(email=email, oauth_provider=oauth_provider)

        company_invitations = CompanyInvitation.get_by_email(email)

        if company_invitations:
            notification = Notification(
                user=user,
                json_data=NotificationLayout(
                    title="You got invited to a company!",
                    msg="Click here to accept the invitation.",
                    type="system",
                    item=NotificationItem(
                        url=url_for("settings.company_list_view"),
                        type="info",
                    ),
                ).model_dump(),
            )
            db.session.add(notification)

        db.session.add(user)
        db.session.commit()
        return user

    if user.oauth_provider != oauth_provider:  # type: ignore
        raise Exception(OAUTH_MISMATCHED_PROVIDER)

    return user


def api_call(url: str, access_token: str):
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    return response


@auth.route("/fetch-time/<int:user_id>", methods=["GET"])
@login_required
@check_user_info_complete
def fetch_time(user_id):
    if not user_id:
        return jsonify({"error": "User ID is required"})

    email_verification = EmailVerification.get_last_unused_by_user_id(user_id)
    if email_verification and not email_verification.is_resendable:
        created_at = email_verification.created_at.replace(tzinfo=datetime.UTC, microsecond=0)
        utc_now = datetime.datetime.now(datetime.UTC).replace(
            microsecond=0,
        )
        time_left = 60 - (utc_now - created_at).total_seconds()
        return jsonify({"time_left": time_left})

    return jsonify({"time_left": 0})


@auth.route("/verify-email")
@login_required
@check_user_info_complete
def verify_email():
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    token = request.args.get("uuid", "")
    next_url = request.args.get("next")
    email_verification = EmailVerification.get_by_token(token)
    user = User.get_by_id(email_verification.user_id) if email_verification else None

    if not email_verification or not user or user.id != authenticated_user.id:
        notification = Notification(
            user=authenticated_user,
            json_data=NotificationLayout(title="Invalid code", msg="The code you have entered is invalid").model_dump(),
            destination=NotificationDestination.VERIFICATION,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("auth.email_verification_required", next=next_url))

    if email_verification.is_expired:
        notification = Notification(
            user=authenticated_user,
            json_data=NotificationLayout(title="Code expired", msg="The code has already expired!").get_json(),
            destination=NotificationDestination.VERIFICATION,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("auth.email_verification_required", next=next_url))

    authenticated_user.is_verified = True
    email_verification.is_used = True
    db.session.commit()

    return redirect(url_for("main.search", next=next_url))


@auth.route("/resend-verification/<int:user_id>")
@login_required
@check_user_info_complete
def resend_verification_email(user_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    user = User.get_by_id(user_id)

    if not user or user.id != authenticated_user.id:
        status = Status(
            StatusType.ERROR, ACCOUNT_NOT_FOUND
        ).get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    if user.is_verified:
        return redirect(url_for("main.search", _external=False))

    last_verification = EmailVerification.get_last_unused_by_user_id(user_id)

    if last_verification:
        if not last_verification.is_resendable:
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(
                    title="Hey! Slow down..", msg="You can only request a new code every minute."
                ).model_dump(),
                destination=NotificationDestination.VERIFICATION,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("auth.email_verification_required", _external=False))

    EmailVerification.expire_all_by_user_id(user_id)

    verification = EmailVerification(user_id=user_id)
    db.session.add(verification)
    db.session.commit()

    google_pubsub.send_event(
        "A user has requested a new verification code!",
        email=user.email,
        event_type=Events.USER_COMPLETED_ONBOARDING.value,
        random_key=verification.token,
    )

    notification = Notification(
        user=authenticated_user,
        json_data=NotificationLayout(
            title="Verification code sent!",
            msg="Please check your email for the new verification code. It may take a few minutes to arrive.",
        ).model_dump(),
        destination=NotificationDestination.VERIFICATION,
    )
    db.session.add(notification)
    db.session.commit()

    return redirect(url_for("main.search"))


@auth.route("/email-verification", methods=["GET", "POST"])
@login_required
@check_user_info_complete
def email_verification_required():
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    next_url = request.args.get("next")

    if authenticated_user.is_verified:
        return redirect(url_for("main.search", next=next_url))

    notifications = Notification.get_unread(
        user_id=authenticated_user.id,
        destination=NotificationDestination.VERIFICATION,
    )
    return render_template("verify_email.html", user_id=current_user.id, notifications=notifications)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.search"))
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template("auth/login.html", status_type=status_type, msg=msg)


@auth.route("/login-linkedin")
def linkedin_login():
    return oauth.linkedin.authorize_redirect(  # type: ignore
        redirect_uri=url_for("auth.linkedin_callback", _external=True)
    )


@auth.route("/linkedin-oauth")
def linkedin_callback():
    # BUG: For some reason client_secret is not being passed during
    # app initialization. Hardcoding it for now.
    # NOTE: Making this the only OAuth provider doesn't fix the issue.
    authorization = oauth.linkedin.authorize_access_token(client_secret=LINKEDIN_SECRET)  # type: ignore
    access_token = authorization.get("access_token")

    if not authorization:
        status = Status(StatusType.ERROR, OAUTH_ACCESS_TOKEN).get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    email_data = api_call(
        url=LINKEDIN_EMAIL_URL,
        access_token=access_token,
    )
    if not email_data or "elements" not in email_data:
        status = Status(StatusType.ERROR, OAUTH_COULD_NOT_RETRIEVE_DATA).get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    email = email_data.get("elements")[0].get("handle~").get("emailAddress")
    if not email:
        status = Status(StatusType.ERROR, OAUTH_NO_EMAIL).get_status()
        return redirect(url_for("auth.login", _external=False, **status))
    user_info_response = api_call(
        url=LINKEDIN_PERSONAL_INFO_URL,
        access_token=access_token,
    )
    if not user_info_response:
        status = Status(StatusType.ERROR, OAUTH_COULD_NOT_RETRIEVE_DATA).get_status()
        return redirect(url_for("auth_login", _external=False, **status))

    first_name = user_info_response.get("localizedFirstName")
    last_name = user_info_response.get("localizedLastName")

    try:
        user = oauth_user(email, OauthProvider.LINKEDIN)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    user.oauth_provider = OauthProvider.LINKEDIN
    db.session.commit()

    user_info = UserInfo.get_by_user_id(user.id)
    if not user_info:
        user_info = UserInfo(
            user=user,
            first_name=first_name,
            last_name=last_name,
        )

        db.session.add(user_info)
        db.session.commit()

    user_payment = UserPayment.get_by_user_id(user.id)
    if not user_payment:
        user_payment = UserPayment(user=user)
        db.session.add(user_payment)
        db.session.commit()

    login_user(user, remember=True)

    if not user_info.is_complete:
        return redirect(url_for("onboarding.index"))

    return redirect(url_for("main.search"))


@auth.route("/login-google")
def google_login():
    return oauth.google.authorize_redirect(  # type: ignore
        redirect_uri=url_for("auth.google_callback", _external=True),
    )


@auth.route("/google-oauth")
def google_callback():
    try:
        authorization = oauth.google.authorize_access_token()  # type: ignore
        if not authorization:
            status = Status(StatusType.ERROR, OAUTH_ACCESS_TOKEN).get_status()
            return redirect(url_for("auth.login", _external=False, **status))
    except Exception:
        return redirect(url_for("auth.google_login"))

    google_user_info = authorization.get("userinfo")
    if not google_user_info:
        status = Status(StatusType.ERROR, OAUTH_NO_USER_INFO).get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    email = google_user_info.get("email")
    if not email:
        status = Status(StatusType.ERROR, OAUTH_NO_EMAIL).get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    try:
        user = oauth_user(email, OauthProvider.GOOGLE)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    user_info = UserInfo.get_by_user_id(user.id)
    if not user_info:
        user_info = UserInfo(
            user=user,
            first_name=google_user_info.get("given_name"),
            last_name=google_user_info.get("family_name"),
        )

        db.session.add(user_info)
        db.session.commit()

    user_payment = UserPayment.get_by_user_id(user.id)
    if not user_payment:
        user_payment = UserPayment(user=user)
        db.session.add(user_payment)
        db.session.commit()

    login_user(user, remember=True)

    if not user_info.is_complete:
        return redirect(url_for("onboarding.index"))

    return redirect(url_for("main.search"))


@auth.get("/username/<username>")
@login_required
def username(username: str):
    return jsonify({"is_taken": UserInfo.is_taken(username)})


@auth.route("/tier-selection")
@login_required
@check_verification
@check_user_info_complete
def tier_selection():
    return render_template("auth/tier_selection.html")


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
