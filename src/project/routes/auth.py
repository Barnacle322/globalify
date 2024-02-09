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
from ..models import Company, User, UserInfo, UserPayment
from ..utils.enums import OauthProvider, Status, StatusType
from ..utils.errors.error_messages import (
    AUTH_FIELDS_INCOMPLETE,
    AUTH_USERNAME_USED,
    OAUTH_ACCESS_TOKEN,
    OAUTH_COULD_NOT_RETRIEVE_DATA,
    OAUTH_MISMATCHED_PROVIDER,
    OAUTH_NO_EMAIL,
    OAUTH_NO_USER_INFO,
)

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
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    if user_info.is_complete:
        return redirect(url_for("auth.company_form"))

    if request.method == "POST":
        first_name, last_name, username, company_name = (
            request.form.get("first_name"),
            request.form.get("last_name"),
            request.form.get("username"),
            request.form.get("company_name"),
        )

        if not first_name or not last_name or not username or not company_name:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(url_for("auth.onboarding", _external=False, **status))

        if UserInfo.is_taken(username):
            status = Status(StatusType.ERROR, AUTH_USERNAME_USED).get_status()
            return redirect(url_for("auth.onboarding", _external=False, **status))

        user_info.first_name = first_name
        user_info.last_name = last_name
        user_info.username = username

        if not Company.get_by_user_id(authenticated_user.id):
            company = Company(user_id=authenticated_user.id, name=company_name)
            db.session.add(company)

        user_info.is_complete = True

        db.session.commit()
        status = Status(
            StatusType.SUCCESS,
            "Add some more info to get better results!",
        ).get_status(
            title="You have registered!",
            button_text="Go!",
            button_url=url_for("auth.expanded_onboarding", _external=False),
        )

        return redirect(url_for("main.search", _external=False, **status))

    return render_template(
        "auth/onboarding.html",
        user_info=user_info.sanitize(),
        status_type=status_type,
        msg=msg,
    )


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
