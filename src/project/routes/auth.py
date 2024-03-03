import datetime
import os
import re

import requests
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

from ..extensions import db, login_manager, oauth
from ..models import Company, Country, EmailVerification, Industry, Notification, Round, User, UserInfo, UserPayment

# from ..utils.email_verification import create_verification_token
from ..utils.enums import (
    ButtonLayout,
    Events,
    NotificationDestination,
    NotificationLayout,
    OauthProvider,
    Status,
    StatusType,
)
from ..utils.errors.error_messages import (
    AUTH_FIELDS_INCOMPLETE,
    AUTH_USERNAME_USED,
    OAUTH_ACCESS_TOKEN,
    OAUTH_COULD_NOT_RETRIEVE_DATA,
    OAUTH_MISMATCHED_PROVIDER,
    OAUTH_NO_EMAIL,
    OAUTH_NO_USER_INFO,
)
from ..utils.google_helpers.google_pubsub import send_event
from .main import check_user_info_complete, check_verification
from .payment import waitlist as payment_waitlist

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
    """
    Authenticates and retrieves a user based on the email and OAuth provider.

    If the user does not exist, a new user is created and returned.
    If the user exists but the OAuth provider is different, an exception is raised.
    If the user exists and the OAuth provider is correct, the existing user is returned.

    Args:
        email (str): The email of the user.
        oauth_provider (OauthProvider): The OAuth provider.

    Returns:
        User: The authenticated user.

    Raises:
        Exception: If the user exists but the OAuth provider is different.
    """
    user = User.get_by_email(email)
    if not user:
        user = User(email=email, oauth_provider=oauth_provider)
        db.session.add(user)
        db.session.commit()
        return user

    if user.oauth_provider != oauth_provider:  # type: ignore
        raise Exception(OAUTH_MISMATCHED_PROVIDER)

    return user


def api_call(url: str, access_token: str):
    """
    Performs an API call to the specified URL using the provided access token.

    Args:
        url (str): The URL to make the API call to.
        access_token (str): The access token to authenticate the API call.

    Returns:
        dict: The JSON response from the API call.
    """
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
    email_verification = EmailVerification.get_by_token(token)

    if not email_verification:
        notification = Notification(
            user=authenticated_user,
            json_data=NotificationLayout(title="Invalid code", msg="The code you have put in is invalid").get_json(),
            destination=NotificationDestination.VERIFICATION,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("auth.email_verification_required"))

    user = User.get_by_id(email_verification.user_id)

    if not user or user.id != authenticated_user.id:
        status = Status(
            StatusType.ERROR, "Hmm, we couldn't find your account. Please reach out to our support team!"
        ).get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    if email_verification.is_expired:
        notification = Notification(
            user=authenticated_user,
            json_data=NotificationLayout(title="Error", msg="Email verification code has expired.").get_json(),
            destination=NotificationDestination.VERIFICATION,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("auth.email_verification_required"))

    try:
        authenticated_user.is_verified = True
        email_verification.is_used = True
        db.session.commit()
    except Exception:
        notification = Notification(
            user=authenticated_user,
            json_data=NotificationLayout(
                title="Error", msg="Something went wrong! Please reach out to our support team!"
            ).get_json(),
            destination=NotificationDestination.VERIFICATION,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("auth.email_verification_required"))

    return redirect(url_for("main.search"))


@auth.route("/resend-verification/<user_id>")
@login_required
@check_user_info_complete
def resend_verification_email(user_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    user = User.get_by_id(user_id)

    if not user or user.id != authenticated_user.id:
        status = Status(
            StatusType.ERROR, "Hmm, we couldn't find your account. Please reach out to our support team!"
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
                ).get_json(),
                destination=NotificationDestination.VERIFICATION,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("auth.email_verification_required", _external=False))

    EmailVerification.expire_all_by_user_id(user_id)

    verification = EmailVerification(user_id=user_id)
    db.session.add(verification)
    db.session.commit()

    send_event(
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
        ).get_json(),
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

    if authenticated_user.is_verified:
        return redirect(url_for("main.search"))

    notifications = Notification.get_unread(
        user_id=authenticated_user.id,
        destination=NotificationDestination.VERIFICATION,
    )
    return render_template("verify_email.html", user_id=current_user.id, notifications=notifications)


@auth.route("/login", methods=["GET", "POST"])
def login():
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
    """
    Handles the callback from LinkedIn OAuth login.

    Retrieves the access token from the authorization response.
    Makes API calls to retrieve the user's email and personal info from LinkedIn.
    Creates or updates the user and user info records in the database.
    Logs in the user and redirects to the appropriate page.
    """
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
    if not email_data:
        status = Status(StatusType.ERROR, OAUTH_COULD_NOT_RETRIEVE_DATA).get_status()
        return redirect(url_for("auth_login", _external=False, **status))

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
        return redirect(url_for("auth.onboarding"))

    return redirect(url_for("main.search"))


@auth.route("/login-google")
def google_login():
    return oauth.google.authorize_redirect(  # type: ignore
        redirect_uri=url_for("auth.google_callback", _external=True),
    )


@auth.route("/google-oauth")
def google_callback():
    """
    Handles the callback from Google OAuth login.

    Retrieves the access token from the authorization response.
    Makes API calls to retrieve the user's email and personal info from Google.
    Creates or updates the user and user info records in the database.
    Logs in the user and redirects to the appropriate page.
    """
    authorization = oauth.google.authorize_access_token()  # type: ignore
    if not authorization:
        status = Status(StatusType.ERROR, OAUTH_ACCESS_TOKEN).get_status()
        return redirect(url_for("auth.login", _external=False, **status))

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
        return redirect(url_for("auth.onboarding"))

    return redirect(url_for("main.search"))


@auth.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    """
    Handles the onboarding process for authenticated users.

    If the current user is anonymous, it redirects to the login page.
    If user_info is not found for the authenticated user, it redirects to the login page.
    If user_info.is_complete is True, it redirects to the company_form route.
    If the request method is POST, it processes the onboarding form data and updates the user's information.
    """
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    notifications = Notification.get_unread(
        user_id=authenticated_user.id,
        destination=NotificationDestination.ONBOARDING,
        is_read=False,
    )

    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    if user_info.is_complete:
        return redirect(url_for("auth.onboarding"))

    if request.method == "POST":
        first_name, last_name, username, company_name = (
            request.form.get("first_name"),
            request.form.get("last_name"),
            request.form.get("username"),
            request.form.get("company_name"),
        )

        if not first_name or not last_name or not username or not company_name:
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(title="Error!", msg=AUTH_FIELDS_INCOMPLETE).get_json(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("auth.onboarding"))

        if UserInfo.is_taken(username):
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(title="Error!", msg=AUTH_USERNAME_USED).get_json(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("auth.onboarding"))

        username_regex = r"^[a-zA-Z0-9]{4,20}$"
        if not re.match(username_regex, username):
            notification = Notification(
                user=authenticated_user,
                json_data=NotificationLayout(
                    title="Error!",
                    msg="Username should be 4 to 20 characters long and should only have alphanumeric values.",
                ).get_json(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("auth.onboarding"))

        user_info.first_name = first_name
        user_info.last_name = last_name
        user_info.username = username.lower()

        if not Company.get_by_user_id(authenticated_user.id):
            company = Company(user_id=authenticated_user.id, name=company_name)
            db.session.add(company)

        user_info.is_complete = True

        db.session.commit()

        notification = Notification(
            user=authenticated_user,
            json_data=NotificationLayout(
                title="Welcome!",
                msg="To get better recommendations, complete your profile.",
                buttons=[
                    ButtonLayout(text="Go!", url=url_for("auth.expanded_onboarding"), dismiss=False),
                ],
                is_closable=False,
            ).get_json(),
            destination=NotificationDestination.SEARCH,
        )
        db.session.add(notification)
        db.session.commit()

        verification = EmailVerification(user_id=authenticated_user.id)
        db.session.add(verification)
        db.session.commit()
        send_event(
            "A new user has completed onboarding!",
            email=authenticated_user.email,
            event_type=Events.USER_COMPLETED_ONBOARDING.value,
            random_key=verification.token,
        )

        return redirect(url_for("main.search"))

    return render_template("auth/onboarding.html", user_info=user_info.sanitize(), notifications=notifications)


@auth.get("/username/<username>")
@login_required
def username(username: str):
    """
    Checks if a username is already taken.

    Args:
        username (str): The username to check.
    """
    return jsonify({"is_taken": UserInfo.is_taken(username)})


@auth.route("/expanded-onboarding", methods=["GET", "POST"])
@login_required
@check_verification
@check_user_info_complete
def expanded_onboarding():
    """
    Handles the expanded onboarding process for authenticated users.

    If the current user is anonymous, it redirects to the login page.
    If user_info is not found for the authenticated user, it redirects to the login page.
    If user_info.is_complete is False, it redirects to the onboarding route.
    If the request method is POST, it processes the expanded onboarding form data and updates the user's information.
    """
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    industries = Industry.get_all()
    rounds = Round.get_all()
    countries = Country.get_all()
    company = Company.get_by_user_id(current_user.id)
    if not company:
        return redirect(url_for("auth.onboarding"))

    if request.method == "POST":
        company_name = request.form.get("company_name")
        industry_id = request.form.get("industry", type=int)
        round_id = request.form.get("round", type=int)
        country_id = request.form.get("country", type=int)
        website = request.form.get("website")

        if not company_name or not industry_id or not round_id or not country_id:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(url_for("auth.expanded_onboarding", _external=False, **status))

        industry = Industry.get_by_id(industry_id)
        round = Round.get_by_id(round_id)
        country = Country.get_by_id(country_id)

        if not industry or not round or not country:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(url_for("auth.expanded_onboarding", _external=False, **status))

        company.name = company_name
        company.industry = industry
        company.preferred_round = round
        company.country = country
        company.website_url = website

        db.session.commit()

        return payment_waitlist(
            email=authenticated_user.email,
            first_name=authenticated_user.user_info.first_name,  # type: ignore
            last_name=authenticated_user.user_info.last_name,  # type: ignore
            user=authenticated_user,
        )

    return render_template(
        "auth/expanded_onboarding.html",
        industries=industries,
        rounds=rounds,
        countries=countries,
        company_name=company.name,
        status_type=status_type,
        msg=msg,
    )


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
