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
from ..utils.google_storage import prepare_picture, upload_blob
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
    - No User -> create and return new User
    - User exists, but OAuth provider is different -> raise Exception
    - User exists, OAuth provider is correct -> return User
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
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
    ).json()

    return response


@auth.route("/register", methods=["GET", "POST"])
def register():
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
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    if user_info.is_complete:
        return redirect(url_for("auth.company_form"))

    if request.method == "POST":
        first_name, last_name, username = (
            request.form.get("first-name"),
            request.form.get("last-name"),
            request.form.get("username"),
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
        user_info.bio = request.form.get("about")
        user_info.language = request.form.get("language")  # type: ignore
        user_info.linkedin = request.form.get("linkedin")
        user_info.instagram = request.form.get("instagram")
        user_info.twitter = request.form.get("twitter")
        user_info.is_complete = True

        # TODO: Add a UI warning for this
        if pfp := request.files["pfp"]:
            try:
                resized_pfp = prepare_picture(pfp)

                pfp_uuid = upload_blob(resized_pfp.read())
                user_info.pfp_uuid = str(pfp_uuid)
            except Exception as e:
                print(f"An error occurred: {e}")

        db.session.commit()
        return redirect(url_for("auth.company_form"))

    return render_template("auth/onboarding.html", languages=language_list, user_info=user_info.sanitize())


@auth.get("/username/<username>")
@login_required
def username(username: str):
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    is_taken = UserInfo.is_taken(username)

    return jsonify({"is_taken": is_taken})


@auth.route("/company-form", methods=["GET", "POST"])
@login_required
def company_form():
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
        company = Company(
            user_id=authenticated_user.id,
            name=request.form.get("company-name"),
            description=request.form.get("about"),
            country_id=request.form.get("country"),
            preferred_round_id=request.form.get("round"),
            industry_id=request.form.get("industry"),
            website=request.form.get("website"),
        )

        if pfp := request.files["pfp"]:
            try:
                resized_pfp = prepare_picture(pfp)
                pfp_uuid = upload_blob(resized_pfp.read())
                company.pfp_uuid = str(pfp_uuid)
            except Exception as e:
                print(f"An error occurred: {e}")

        db.session.add(company)
        db.session.commit()
        return redirect(url_for("main.dashboard"))

    return render_template(
        "auth/company_form.html",
        industries=industries,
        rounds=rounds,
        countries=countries,
    )


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
