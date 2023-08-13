import os
import re
from typing import Any

import requests
from ..error_messages import (
    AUTH_EMAIL_NOT_FOUNDS,
    AUTH_EMAIL_USED,
    AUTH_FIELDS_INCOMPLETE,
    AUTH_INCORRECT_PASSWORD,
    AUTH_INVALID_EMAIL,
    AUTH_MISMATCHED_PASSWORDS,
    AUTH_OAUTH_USED,
    OAUTH_ACCESS_TOKEN,
    OAUTH_MISMATCHED_PROVIDER,
    OAUTH_NO_EMAIL,
    OAUTH_NO_USER_INFO,
)
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from ..extensions import db, login_manager, oauth
from ..models import OauthProvider, User, UserInfo
from ..utils import Status, StatusType

auth = Blueprint("auth", __name__)

LINKEDIN_SECRET = os.environ.get("_LINKEDIN_OAUTH2_CLIENT_SECRET")
LINKEDIN_EMAIL_URL = (
    "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
)
LINKEDIN_PERSONAL_INFO_URL = "https://api.linkedin.com/v2/me"


@login_manager.user_loader
def load_user(user_id: int) -> User:
    return User.get_by_id(user_id)


def oauth_user(email: str, oauth_provider: OauthProvider):
    """
    - No User -> create and return new User
    - User exists, but OAuth provider is different -> return False
    - User exists, OAuth provider is correct -> return User
    """
    user = User.get_by_email(email)
    if not user:
        user = User(email=email)  # type: ignore
        db.session.add(user)
        db.session.commit()
        return user

    return False if user.oauth_provider != oauth_provider else user


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
        new_user.password = password

        db.session.add(new_user)
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

        login_user(user)
        return redirect(url_for("main.index"))

    return render_template("login.html", status_type=status_type, msg=msg)


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

    email = email_response.get("elements")[0].get("handle~").get("emailAddress")
    if not email:
        status = Status(StatusType.ERROR, OAUTH_NO_EMAIL).get_status()
        return redirect(url_for("auth.login", **status))  # type: ignore

    user_info_response = api_call(
        url=LINKEDIN_PERSONAL_INFO_URL,
        access_token=access_token,
    )
    first_name = user_info_response.get("localizedFirstName")
    last_name = user_info_response.get("localizedLastName")

    user = oauth_user(email, OauthProvider.LINKEDIN)
    if not user:
        status = Status(StatusType.ERROR, OAUTH_MISMATCHED_PROVIDER).get_status()
        return redirect(url_for("auth.login", **status))  # type: ignore

    user_info = UserInfo(
        user_id=user.id,
        user=user,
        first_name=first_name,
        last_name=last_name,
    )
    db.session.add(user_info)
    user.oauth_provider = OauthProvider.LINKEDIN
    db.session.commit()
    login_user(user)

    return redirect(url_for("main.index"))


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

    user_info = authorization.get("userinfo")
    if not user_info:
        status = Status(StatusType.ERROR, OAUTH_NO_USER_INFO).get_status()
        return redirect(url_for("auth.login", **status))  # type: ignore

    email: str = user_info.get("email")
    if not email:
        status = Status(StatusType.ERROR, OAUTH_NO_EMAIL).get_status()
        return redirect(url_for("auth.login", **status))  # type: ignore

    user = oauth_user(email, OauthProvider.GOOGLE)
    if not user:
        status = Status(StatusType.ERROR, OAUTH_MISMATCHED_PROVIDER).get_status()
        return redirect(url_for("auth.login", **status))  # type: ignore

    user.oauth_provider = OauthProvider.GOOGLE
    user_info = UserInfo(
        user_id=user.id,
        user=user,
        first_name=user_info.get("given_name"),
        last_name=user_info.get("family_name"),
    )
    db.session.add(user_info)
    db.session.commit()
    login_user(user)

    return redirect(url_for("main.index"))


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
