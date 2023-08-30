import io
import os
import re
from typing import Any

import requests
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from PIL import Image

from ..error_messages import (
    AUTH_EMAIL_NOT_FOUNDS,
    AUTH_EMAIL_USED,
    AUTH_FIELDS_INCOMPLETE,
    AUTH_INCORRECT_PASSWORD,
    AUTH_INVALID_EMAIL,
    AUTH_MISMATCHED_PASSWORDS,
    AUTH_OAUTH_USED,
    OAUTH_ACCESS_TOKEN,
    OAUTH_COULD_NOT_RETRIEVE_DATA,
    OAUTH_MISMATCHED_PROVIDER,
    OAUTH_NO_EMAIL,
    OAUTH_NO_USER_INFO,
)
from ..extensions import db, login_manager, oauth
from ..google_storage import upload_blob
from ..models import User, UserInfo
from ..utils import OauthProvider, Status, StatusType

auth = Blueprint("auth", __name__)

LINKEDIN_SECRET = os.environ.get("_LINKEDIN_OAUTH2_CLIENT_SECRET")
LINKEDIN_EMAIL_URL = (
    "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
)
LINKEDIN_PERSONAL_INFO_URL = "https://api.linkedin.com/v2/me"


@login_manager.user_loader
def load_user(user_id: int) -> User:
    return User.get_by_id(user_id)


def oauth_user(email: str, oauth_provider: OauthProvider) -> User:
    """
    - No User -> create and return new User
    - User exists, but OAuth provider is different -> raise Exception
    - User exists, OAuth provider is correct -> return User
    """
    user = User.get_by_email(email)
    if not user:
        user = User(email=email)  # type: ignore
        db.session.add(user)
        db.session.commit()
        return user

    if user.oauth_provider != oauth_provider:
        raise Exception(OAUTH_MISMATCHED_PROVIDER)

    return user


def api_call(url: str, access_token: str) -> Any:
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
            return redirect(url_for("auth.register", **status))  # type: ignore

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            status = Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status()
            return redirect(url_for("auth.register", **status))  # type: ignore

        if password != confirm_password:
            status = Status(StatusType.ERROR, AUTH_MISMATCHED_PASSWORDS).get_status()
            return redirect(url_for("auth.register", **status))  # type: ignore

        if oauth := User.signed_with_oauth(email):
            status = Status(
                StatusType.WARNING, AUTH_OAUTH_USED.format(oauth.value.capitalize())  # type: ignore
            ).get_status()
            return redirect(url_for("auth.register", **status))  # type: ignore

        user = User.get_by_email(email)
        if user:
            status = Status(StatusType.ERROR, AUTH_EMAIL_USED).get_status()
            return redirect(url_for("auth.register", **status))  # type: ignore

        new_user = User(email=email)  # type: ignore
        new_user_info = UserInfo(user_id=new_user.id)  # type: ignore
        new_user.password = password

        db.session.add(new_user)
        db.session.add(new_user_info)
        db.session.commit()

        return redirect(url_for("auth.login"))

    return render_template("register.html", status_type=status_type, msg=msg)


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
            return redirect(url_for("auth.login", **status))  # type: ignore

        user = User.get_by_email(email)
        if not user:
            status = Status(StatusType.ERROR, AUTH_EMAIL_NOT_FOUNDS).get_status()
            return redirect(url_for("auth.login", **status))  # type: ignore

        if oauth := User.signed_with_oauth(email):
            status = Status(
                StatusType.WARNING, AUTH_OAUTH_USED.format(oauth.value.capitalize())  # type: ignore
            ).get_status()
            return redirect(url_for("auth.login", **status))  # type: ignore

        if not user.verify_password(password):
            status = Status(StatusType.ERROR, AUTH_INCORRECT_PASSWORD).get_status()
            return redirect(url_for("auth.login", **status))  # type: ignore

        login_user(user, remember=True)

        user_info = UserInfo.get_by_user_id(user.id)
        if user_info and not user_info.is_complete:
            return redirect(url_for("auth.login_form"))
        else:
            return redirect(url_for("main.dashboard"))

    return render_template("login.html", status_type=status_type, msg=msg)


@auth.route("/login-form", methods=["GET", "POST"])
@login_required
def login_form():
    authenticated_user: User = current_user  # type: ignore
    if not authenticated_user:
        return redirect(url_for("auth.login"))

    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info:
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        first_name = request.form.get("first-name")
        last_name = request.form.get("last-name")
        username = request.form.get("username")
        about = request.form.get("about")
        linkedin = request.form.get("linkedin")
        instagram = request.form.get("instagram")

        if pfp := request.files["pfp"]:
            pfp_image = Image.open(io.BytesIO(pfp.read()))
            pfp_image.thumbnail((500, 500))

            resized_pfp = io.BytesIO()
            pfp_image.save(resized_pfp, format="JPEG")
            resized_pfp.seek(0)

            pfp_uuid = upload_blob(resized_pfp.read())
            user_info.pfp_uuid = str(pfp_uuid)  # type: ignore

        user_info.first_name = first_name  # type: ignore
        user_info.last_name = last_name  # type: ignore
        user_info.username = username  # type: ignore
        user_info.bio = about  # type: ignore
        user_info.linkedin = linkedin  # type: ignore
        user_info.instagram = instagram  # type: ignore
        user_info.is_complete = True

        db.session.commit()
        return redirect(url_for("main.dashboard"))

    # TODO: Add languages to database
    languages = ["English", "Spanish", "French", "German", "Italian", "Portuguese"]
    return render_template(
        "login_form.html", languages=languages, user_info=user_info.sanitize()
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
    authorization = oauth.linkedin.authorize_access_token(client_secret=LINKEDIN_SECRET)  # type: ignore
    access_token = authorization.get("access_token")

    if not authorization:
        status = Status(StatusType.ERROR, OAUTH_ACCESS_TOKEN).get_status()
        return redirect(url_for("auth.login", **status))  # type: ignore

    email_response = api_call(
        url=LINKEDIN_EMAIL_URL,
        access_token=access_token,
    )
    if not email_response:
        status = Status(StatusType.ERROR, OAUTH_COULD_NOT_RETRIEVE_DATA).get_status()
        return redirect(url_for("auth_login"), **status)  # type: ignore

    email = email_response.get("elements")[0].get("handle~").get("emailAddress")
    if not email:
        status = Status(StatusType.ERROR, OAUTH_NO_EMAIL).get_status()
        return redirect(url_for("auth.login", **status))  # type: ignore

    user_info_response = api_call(
        url=LINKEDIN_PERSONAL_INFO_URL,
        access_token=access_token,
    )
    if not user_info_response:
        status = Status(StatusType.ERROR, OAUTH_COULD_NOT_RETRIEVE_DATA).get_status()
        return redirect(url_for("auth_login"), **status)  # type: ignore

    first_name = user_info_response.get("localizedFirstName")
    last_name = user_info_response.get("localizedLastName")

    try:
        user = oauth_user(email, OauthProvider.LINKEDIN)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("auth.login"), **status)  # type: ignore

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

    login_user(user, remember=True)

    if not user_info.is_complete:
        return redirect(url_for("auth.login_form"))
    else:
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
        return redirect(url_for("auth.login", **status))  # type: ignore

    google_user_info = authorization.get("userinfo")
    if not google_user_info:
        status = Status(StatusType.ERROR, OAUTH_NO_USER_INFO).get_status()
        return redirect(url_for("auth.login", **status))  # type: ignore

    email = google_user_info.get("email")
    if not email:
        status = Status(StatusType.ERROR, OAUTH_NO_EMAIL).get_status()
        return redirect(url_for("auth.login", **status))  # type: ignore

    try:
        user = oauth_user(email, OauthProvider.GOOGLE)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("auth.login"), **status)  # type: ignore

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

    login_user(user, remember=True)

    if not user_info.is_complete:
        return redirect(url_for("auth.login_form"))
    else:
        return redirect(url_for("main.dashboard"))


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
