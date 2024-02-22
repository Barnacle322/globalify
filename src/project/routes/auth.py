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
from ..utils.email_verification import create_verification_token, update_is_expired
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

    if user.oauth_provider != oauth_provider:
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


@auth.route("/fetch-time", methods=["GET"])
def fetch_time():
    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"error": "User ID is required"})

    email_verification = EmailVerification.fetch_email_verification(int(user_id))
    if email_verification:
        created_at = email_verification.created_at
        return jsonify({"created_at": created_at})
    else:
        return jsonify({"error": "EmailVerification object not found"})


@login_required
@auth.route("/verify-email/")
def verify_email():
    token = request.args.get("uuid", "")

    email_verification = EmailVerification.get_by_token(token)

    if not email_verification:
        notification = Notification(
            user_id=current_user.id,
            json_data=NotificationLayout("Error", "The email verification code is invalid.").get_json(),
            destination=NotificationDestination.VERIFICATION,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("auth.email_verification_required", _external=False))

    if email_verification.is_used:
        notification = Notification(
            user_id=current_user.id,
            json_data=NotificationLayout("Error", "The email verification code has already been used.").get_json(),
            destination=NotificationDestination.SEARCH,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("auth.email_verification_required", _external=False))

    user = User.get_by_id(email_verification.user_id)

    if not user:
        status = Status(StatusType.ERROR, "User not found.").get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    if user.is_verified:
        notification = Notification(
            user_id=current_user.id,
            json_data=NotificationLayout("Error", "The user is already verified.").get_json(),
            destination=NotificationDestination.SEARCH,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("auth.email_verification_required", _external=False))

    if email_verification.is_expired:
        notification = Notification(
            user_id=current_user.id,
            json_data=NotificationLayout("Error", "Email verification code has expired.").get_json(),
            destination=NotificationDestination.VERIFICATION,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("auth.email_verification_required", _external=False))

    update_is_expired(email_verification)

    user.is_verified = True
    email_verification.is_used = True
    db.session.commit()

    notification = Notification(
        user_id=current_user.id,
        json_data=NotificationLayout("Success!", "Your email has been verified.").get_json(),
        destination=NotificationDestination.SEARCH,
    )
    db.session.add(notification)
    db.session.commit()

    return redirect(url_for("main.search"))


@auth.route("/resend-verification/<user_id>")
@login_required
def resend_verification_email(user_id):
    user = User.get_by_id(user_id)
    if not user:
        status = Status(StatusType.ERROR, "User not found.").get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    if user.is_verified:
        notification = Notification(
            user_id=current_user.id,
            json_data=NotificationLayout("Error", "The user is already verified.").get_json(),
            destination=NotificationDestination.SEARCH,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("main.search", _external=False))

    last_verification = EmailVerification.fetch_email_verification(user_id)

    if last_verification and not last_verification.is_expired:
        if datetime.datetime.utcnow() - last_verification.created_at < datetime.timedelta(minutes=1):
            notification = Notification(
                user_id=current_user.id,
                json_data=NotificationLayout(
                    "Error", "Please wait for 1 minute before requesting another verification code."
                ).get_json(),
                destination=NotificationDestination.VERIFICATION,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("auth.email_verification_required", _external=False))

    EmailVerification.deactivate_user_tokens(user_id)
    new_verification = create_verification_token(user_id)
    send_event(
        "A new user has completed onboarding!",
        email=user.email,
        event_type=Events.USER_COMPLETED_ONBOARDING.value,
        random_key=new_verification,
    )

    notification = Notification(
        user_id=current_user.id,
        json_data=NotificationLayout(
            "Success!",
            "Good news! Your verification code has been successfully resent. Please check your email inbox for the code.",
        ).get_json(),
        destination=NotificationDestination.VERIFICATION,
    )
    db.session.add(notification)
    db.session.commit()

    return redirect(url_for("main.search"))


@auth.route("/email-verify-required", methods=["GET", "POST"])
def email_verification_required():
    notifications = Notification.fetch_notifications(
        user_id=current_user.id,
        destination=NotificationDestination.VERIFICATION,
        is_read=False,
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
            user_id=user.id,
            user=user,
            first_name=first_name,
            last_name=last_name,
        )

        db.session.add(user_info)
        db.session.commit()

    user_payment = UserPayment.get_by_user_id(user.id)
    if not user_payment:
        user_payment = UserPayment(user_id=user.id)
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
            user_id=user.id,
            user=user,
            first_name=google_user_info.get("given_name"),
            last_name=google_user_info.get("family_name"),
        )

        db.session.add(user_info)
        db.session.commit()

    user_payment = UserPayment.get_by_user_id(user.id)
    if not user_payment:
        user_payment = UserPayment(user_id=user.id)
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

    notifications = Notification.fetch_notifications(
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
                user_id=current_user.id,
                json_data=NotificationLayout("Error!", AUTH_FIELDS_INCOMPLETE).get_json(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("auth.onboarding"))

        if UserInfo.is_taken(username):
            notification = Notification(
                user_id=current_user.id,
                json_data=NotificationLayout("Error!", AUTH_USERNAME_USED).get_json(),
                destination=NotificationDestination.ONBOARDING,
            )
            db.session.add(notification)
            db.session.commit()
            return redirect(url_for("auth.onboarding"))

        username_regex = r"^[a-zA-Z0-9]{4,20}$"
        if not re.match(username_regex, username):
            notification = Notification(
                user_id=current_user.id,
                json_data=NotificationLayout(
                    "Error!", "Username should be 4 to 20 characters long and should only have alphanumeric values."
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
            user_id=current_user.id,
            json_data=NotificationLayout(
                "Welcome!",
                "To get better recommendations, complete your profile.",
                [
                    ButtonLayout("Go!", url_for("auth.expanded_onboarding"), False).get_json(),  # type: ignore
                ],
                is_closable=False,
            ).get_json(),
            destination=NotificationDestination.SEARCH,
        )
        db.session.add(notification)
        db.session.commit()

        new_verification = create_verification_token(user_id=authenticated_user.id)
        send_event(
            "A new user has completed onboarding!",
            email=authenticated_user.email,
            event_type=Events.USER_COMPLETED_ONBOARDING.value,
            random_key=new_verification,
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
def expanded_onboarding():
    """
    Handles the expanded onboarding process for authenticated users.

    If the current user is anonymous, it redirects to the login page.
    If user_info is not found for the authenticated user, it redirects to the login page.
    If user_info.is_complete is False, it redirects to the onboarding route.
    If the request method is POST, it processes the expanded onboarding form data and updates the user's information.
    """
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    industries = Industry.get_all()
    rounds = Round.get_all()
    countries = Country.get_all()
    company = Company.get_by_user_id(current_user.id)

    if request.method == "POST":
        company_name = request.form.get("company_name")
        industry_id = request.form.get("industry", type=int)
        round_id = request.form.get("round", type=int)
        country_id = request.form.get("country", type=int)
        website = request.form.get("website")

        print(company_name, industry_id, round_id, country_id, website)
        if not company_name or not industry_id or not round_id or not country_id:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(url_for("auth.expanded_onboarding", _external=False, **status))

        company.name = company_name
        company.industry = Industry.get_by_id(industry_id)
        company.preferred_round = Round.get_by_id(round_id)
        company.country = Country.get_by_id(country_id)
        company.website_url = website

        db.session.commit()

        Notification.mark_notifications_as_read(
            user_id=current_user.id,
            destination=NotificationDestination.SEARCH,
        )

        notification = Notification(
            user_id=current_user.id,
            json_data=NotificationLayout(
                "Onboarding completed!!",
                "Go and try our suggestions!",
                [
                    ButtonLayout("See!", url_for("main.get_suggestions")).get_json(),  # type: ignore
                ],
            ).get_json(),
            destination=NotificationDestination.SEARCH,
        )
        db.session.add(notification)
        db.session.commit()

        return redirect(url_for("main.search"))

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
    """
    Logs out the current user and redirects to the index page.
    """
    logout_user()
    return redirect(url_for("main.index"))
