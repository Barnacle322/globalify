import os
import re

import requests
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

from ..extensions import db, login_manager, oauth
from ..models import Company, Country, Industry, Round, User, UserInfo, UserOauth, UserPayment, UserRegular
from ..utils.errors.auth_error_messages import (
    AUTH_EMAIL_NOT_FOUND,
    AUTH_EMAIL_USED,
    AUTH_FIELDS_INCOMPLETE,
    AUTH_INCORRECT_PASSWORD,
    AUTH_INVALID_EMAIL,
    AUTH_MISMATCHED_PASSWORDS,
    AUTH_OAUTH_USED,
    AUTH_USERNAME_USED,
    OAUTH_ACCESS_TOKEN,
    OAUTH_COULD_NOT_RETRIEVE_DATA,
    OAUTH_MISMATCHED_PROVIDER,
    OAUTH_NO_EMAIL,
    OAUTH_NO_USER_INFO,
)
from ..utils.google_storage import upload_picture
from ..utils.info_lists import languages as language_list
from ..utils.status_enum import OauthProvider, Status, StatusType

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


def oauth_user(email: str, oauth_provider: OauthProvider) -> UserOauth:
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
        user = UserOauth(email=email)
        db.session.add(user)
        db.session.commit()
        return user

    if not isinstance(user, UserOauth):
        raise Exception(AUTH_EMAIL_USED)

    if isinstance(user, UserOauth) and user.oauth_provider != oauth_provider:
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


@auth.route("/register", methods=["GET", "POST"])
def register():
    """
    Handles the registration process for new users.

    If the request method is POST, it processes the registration form data and creates a new user.
    If the request method is GET, it renders the registration page.

    Returns:
        str: The rendered HTML template for the registration page.

    """
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not email or not password or not confirm_password:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(url_for("auth.register", _external=False, **status))

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            status = Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status()
            return redirect(url_for("auth.register", _external=False, **status))

        if password != confirm_password:
            status = Status(StatusType.ERROR, AUTH_MISMATCHED_PASSWORDS).get_status()
            return redirect(url_for("auth.register", _external=False, **status))

        user = User.get_by_email(email)
        if user and isinstance(user, UserOauth):
            status = Status(StatusType.WARNING, AUTH_OAUTH_USED).get_status()
            return redirect(url_for("auth.register", _external=False, **status))

        if user:
            status = Status(StatusType.ERROR, AUTH_EMAIL_USED).get_status()
            return redirect(url_for("auth.register", _external=False, **status))

        new_user = UserRegular(email=email)
        new_user.password = password
        db.session.add(new_user)
        db.session.commit()

        current_app.logger.info(f"User created {new_user}")

        new_user_info = UserInfo(user_id=new_user.id)
        new_user_payment = UserPayment(user_id=new_user.id)
        db.session.add_all((new_user_info, new_user_payment))
        db.session.commit()

        current_app.logger.info(f"UserInfo created {new_user_info}")
        current_app.logger.info(f"UserPayment created {new_user_payment}")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", status_type=status_type, msg=msg)


@auth.route("/login", methods=["GET", "POST"])
def login():
    """
    Handles the login process for users.

    If the request method is POST, it processes the login form data and authenticates the user.
    If the request method is GET, it renders the login page.

    Returns:
        str: The rendered HTML template for the login page.

    """
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(url_for("auth.login", _external=False, **status))

        user = User.get_by_email(email)
        if user and isinstance(user, UserOauth):
            status = Status(StatusType.WARNING, AUTH_OAUTH_USED).get_status()
            return redirect(url_for("auth.register", _external=False, **status))

        if not user:
            status = Status(StatusType.ERROR, AUTH_EMAIL_NOT_FOUND).get_status()
            return redirect(url_for("auth.login", _external=False, **status))

        if isinstance(user, UserRegular) and not user.verify_password(password):
            status = Status(StatusType.ERROR, AUTH_INCORRECT_PASSWORD).get_status()
            return redirect(url_for("auth.login", _external=False, **status))

        login_user(user, remember=True)

        user_info = UserInfo.get_by_user_id(user.id)
        if user_info and not user_info.is_complete:
            return redirect(url_for("auth.onboarding"))

        return redirect(url_for("main.dashboard"))

    return render_template("auth/login.html", status_type=status_type, msg=msg)


@auth.route("/onboarding", methods=["GET", "POST"])
@login_required
def onboarding():
    """
    Handles the onboarding process for authenticated users.

    If the current user is anonymous, it redirects to the login page.
    If user_info is not found for the authenticated user, it redirects to the login page.
    If user_info.is_complete is True, it redirects to the company_form route.
    If the request method is POST, it processes the onboarding form data and updates the user's information.

    Returns:
        str: The rendered HTML template for the onboarding page.

    """
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    if user_info.is_complete:
        return redirect(url_for("auth.company_form"))

    if request.method == "POST":
        first_name, last_name, username, linkedin, instagram, twitter = (
            request.form.get("first_name"),
            request.form.get("last_name"),
            request.form.get("username"),
            request.form.get("linkedin"),
            request.form.get("instagram"),
            request.form.get("twitter"),
        )

        if not first_name or not last_name or not username:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(url_for("auth.onboarding", _external=False, **status))
        is_taken = UserInfo.is_taken(username)
        if is_taken:
            status = Status(StatusType.ERROR, AUTH_USERNAME_USED).get_status()
            return redirect(url_for("auth.onboarding", _external=False, **status))

        user_info.first_name = first_name
        user_info.last_name = last_name
        user_info.username = username

        try:
            user_info.linkedin_url = linkedin
            user_info.instagram_url = instagram
            user_info.twitter_url = twitter
        except ValueError as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("auth.onboarding", _external=False, **status))

        user_info.bio = request.form.get("about")
        user_info.language = request.form.get("language", "English")  # type: ignore
        user_info.is_complete = True

        if picture := request.files.get("pfp"):
            try:
                picture_url = upload_picture(picture)
                user_info.picture_url = picture_url
            except Exception as e:
                status = Status(StatusType.ERROR, f"Error uploading picture: {str(e)}").get_status()
                return redirect(url_for("auth.onboarding", _external=False, **status))

        db.session.commit()
        return redirect(url_for("auth.company_form"))
    return render_template(
        "auth/onboarding.html",
        languages=language_list,
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
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    is_taken = UserInfo.is_taken(username)

    return jsonify({"is_taken": is_taken})


@auth.route("/company-form", methods=["GET", "POST"])
@login_required
def company_form():
    """
    Handles the company form submission for authenticated users.

    If the current user is anonymous, it redirects to the login page.
    If user_info is not found for the authenticated user, it redirects to the login page.
    If a company is already associated with the user, it redirects to the dashboard route.
    If the request method is POST, it processes the company form data and creates a new company entry.

    Returns:
        str: The rendered HTML template for the company form page.

    """
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    company = Company.get_by_user_id(authenticated_user.id)
    if company:
        return redirect(url_for("main.dashboard"))

    industries = Industry.get_all()
    rounds = Round.get_all()
    countries = Country.get_all()

    if request.method == "POST":
        country_id = request.form.get("country", type=int)
        company = Company(
            user_id=authenticated_user.id,
            name=request.form.get("company_name"),
            description=request.form.get("about"),
            country_id=country_id,
            preferred_round_id=request.form.get("round"),
            industry_id=request.form.get("industry"),
            website=request.form.get("website"),
            coordinates=Country.get_by_id(country_id).name,  # type: ignore
        )

        if picture := request.files.get("pfp"):
            try:
                picture_url = upload_picture(picture)
                user_info.picture_url = picture_url
            except Exception as e:
                status = Status(StatusType.ERROR, f"Error uploading picture: {str(e)}").get_status()
                return redirect(url_for("auth.company_form", _external=False, **status))

        db.session.add(company)
        db.session.commit()

        status = Status(StatusType.SUCCESS, "You successfully completed your registration.").get_status()

        return redirect(url_for("main.dashboard", _external=False, **status))

    return render_template(
        "auth/company_form.html",
        industries=industries,
        rounds=rounds,
        countries=countries,
        status_type=status_type,
        msg=msg,
    )


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

    Returns:
        str: The redirect response to the appropriate page.

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

    return redirect(url_for("main.dashboard"))


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

    Returns:
        str: The redirect response to the appropriate page.

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

    user.oauth_provider = OauthProvider.GOOGLE
    db.session.commit()

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

    return redirect(url_for("main.dashboard"))


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
