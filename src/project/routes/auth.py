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
from ..models import Company, EmailVerification, Notification, User, UserInfo, UserPayment
from ..utils.email_verification import create_verification_token, update_is_expired
from ..utils.enums import Events, NotificationDestination, OauthProvider, Status, StatusType
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


@login_required
@auth.route("/verify-email/")
def verify_email():
    """
    Handles the email verification process using the provided token.

    If the token is not found, renders a template with an error message.
    If the token is expired, renders a template indicating that the verification has expired.
    If the user does not exist, aborts the request with a 404 error.
    If the user is already verified, renders a template indicating that the user is already verified.

    Args:
        token (str): The verification token received by the user.
    """
    token = request.args.get("uuid", "")

    email_verification = EmailVerification.get_by_token(token)

    if not email_verification:
        Notification.create_notification(
            user_id=current_user.id,
            title="Error",
            msg="The email verification code is invalid.",
            destination=NotificationDestination.VERIFICATION,
        )
        return redirect(url_for("auth.email_verification_required", _external=False))

    if email_verification.is_used:
        Notification.create_notification(
            user_id=current_user.id,
            title="Error",
            msg="The email verification code has already been used.",
            destination=NotificationDestination.VERIFICATION,
        )
        return redirect(url_for("auth.email_verification_required", _external=False))

    user = User.get_by_id(email_verification.user_id)

    if not user:
        status = Status(StatusType.ERROR, "User not found.").get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    if user.is_verified:
        Notification.create_notification(
            user_id=current_user.id,
            title="Error",
            msg="The user is already verified.",
            destination=NotificationDestination.SEARCH,
        )
        return redirect(url_for("auth.email_verification_required", _external=False))

    if email_verification.is_expired:
        Notification.create_notification(
            user_id=current_user.id,
            title="Error",
            msg="The email verification code has expired.",
            destination=NotificationDestination.VERIFICATION,
        )
        return redirect(url_for("auth.email_verification_required", _external=False))

    update_is_expired(email_verification)

    user.is_verified = True
    email_verification.is_used = True
    db.session.commit()

    Notification.create_notification(
        user_id=current_user.id,
        title="Success!",
        msg="Your email has been verified.",
        destination=NotificationDestination.SEARCH,
    )

    return redirect(url_for("main.search", _external=False))


@auth.route("/resend-verification/<user_id>")
@login_required
def resend_verification_email(user_id):
    """
    Resends the email verification for a user with the given user ID.

    If the user is found:
       a. Checks if the user is not already verified.
       b. Deletes any existing EmailVerification records for the user from the database.
       c. Creates a new EmailVerification record for the user.
       d. Sends an email containing a verification link to the user.
    If the user is already verified, renders a template indicating that the user is already verified.
    If the user is not found, aborts the request with a 404 error.

    Args:
        user_id (str): The user ID for which to resend the email verification.
    """
    user = User.get_by_id(user_id)
    if not user:
        status = Status(StatusType.ERROR, "User not found.").get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    if user.is_verified:
        Notification.create_notification(
            user_id=current_user.id,
            title="Error",
            msg="The user is already verified.",
            destination=NotificationDestination.SEARCH,
        )
        return redirect(url_for("main.search", _external=False))

    last_verification = EmailVerification.fetch_email_verification(user_id)
    print("Arstan",last_verification)

    if last_verification and not last_verification.is_expired:
        if datetime.datetime.utcnow() - last_verification.created_at < datetime.timedelta(minutes=1):
            Notification.create_notification(
                user_id=current_user.id,
                title="Error",
                msg="Please wait for 1 minute before requesting another verification code.",
                destination=NotificationDestination.VERIFICATION,
            )
            return redirect(url_for("auth.email_verification_required", _external=False))

    EmailVerification.deactivate_user_tokens(user_id)
    new_verification = create_verification_token(user_id)
    send_event(
        "A new user has completed onboarding!",
        email=user.email,
        event_type=Events.USER_COMPLETED_ONBOARDING.value,
        random_key=new_verification,
    )

    Notification.create_notification(
        user_id=user_id,
        title="Success!",
        msg="Good news! Your verification code has been successfully resent. Please check your email inbox for the code.",
        destination=NotificationDestination.VERIFICATION,
    )
    db.session.commit()

    return redirect(url_for("main.search"))


@auth.route("/email-verification-required", methods=["GET"])
@login_required
def email_verification_required():
    notifications = Notification.fetch_notifications(
        user_id=current_user.id,
        destination=NotificationDestination.VERIFICATION,
        is_read=False,
    )
    print("Agahan", notifications)
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
            Notification.create_notification(
                user_id=authenticated_user.id,
                title="Error!",
                msg=AUTH_FIELDS_INCOMPLETE,
                destination=NotificationDestination.ONBOARDING,
            )
            return redirect(url_for("auth.onboarding", _external=False))

        if UserInfo.is_taken(username):
            Notification.create_notification(
                user_id=authenticated_user.id,
                title="Error!",
                msg=AUTH_USERNAME_USED,
                destination=NotificationDestination.ONBOARDING,
            )
            return redirect(url_for("auth.onboarding", _external=False))

        user_info.first_name = first_name
        user_info.last_name = last_name
        user_info.username = username

        if not Company.get_by_user_id(authenticated_user.id):
            company = Company(user_id=authenticated_user.id, name=company_name)
            db.session.add(company)

        user_info.is_complete = True

        db.session.commit()

        Notification.create_notification(
            user_id=authenticated_user.id,
            title="Success!",
            msg="Add some more info to get better results!",
            destination=NotificationDestination.SEARCH,
            button_text="Go!",
            button_url=url_for("auth.expanded_onboarding", _external=False),
            icon_url="",
        )

        new_verification = create_verification_token(user_id=authenticated_user.id)
        send_event(
            "A new user has completed onboarding!",
            email=authenticated_user.email,
            event_type=Events.USER_COMPLETED_ONBOARDING.value,
            random_key=new_verification,
        )

        return redirect(url_for("main.search", _external=False))

    return render_template("auth/onboarding.html", user_info=user_info.sanitize(), notifications=notifications)


@auth.get("/username/<username>")
@login_required
def username(username: str):
    """
    Checks if a username is already taken.

    Args:
        username (str): The username to check.

    Returns:
        dict: A JSON response containing the "is_taken" status of the username.
            - "is_taken" (bool): True if the username is already taken, False otherwise.

    """

    is_taken = UserInfo.is_taken(username)

    return jsonify({"is_taken": is_taken})


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

    # authenticated_user: User = current_user._get_current_object()  # type: ignore

    return render_template(
        "auth/expanded_onboarding.html",
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
