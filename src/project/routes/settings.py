import re

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, fresh_login_required, login_required, logout_user

from ..extensions import db
from ..models import User, UserInfo, UserOauth, UserPayment, UserRegular
from ..utils.errors.auth_error_messages import AUTH_INVALID_EMAIL
from ..utils.google_storage import load_pfp
from ..utils.info_lists import languages as language_list
from ..utils.status_enum import Status, StatusType, Tier
from .main import check_user_info_complete, check_verification
from .payment import get_invoices

settings = Blueprint("settings", __name__)


@settings.route("/")
@settings.route("/general")
@login_required
@check_user_info_complete
@check_verification
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    pfp_base64 = load_pfp(authenticated_user.user_info[0].pfp_uuid)  # type: ignore

    return render_template(
        "settings/general.html",
        user=authenticated_user,
        pfp_base64=pfp_base64,
        languages=language_list,
        status_type=status_type,
        msg=msg,
    )


@settings.route("/security")
@login_required
@check_user_info_complete
@check_verification
def security():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    pfp_base64 = load_pfp(authenticated_user.user_info[0].pfp_uuid)  # type: ignore

    return render_template(
        "settings/security.html",
        user=authenticated_user,
        pfp_base64=pfp_base64,
        status_type=status_type,
        msg=msg,
    )


@settings.route("/plan")
@login_required
@check_user_info_complete
@check_verification
def plan():
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    pfp_base64 = load_pfp(authenticated_user.user_info[0].pfp_uuid)  # type: ignore

    user_payment = UserPayment.get_by_user_id(authenticated_user.id)
    subscription = {"tier": Tier.FREE}
    if user_payment and user_payment.customer_id and user_payment.subscription_id:
        subscription = user_payment.sanitize()

    return render_template(
        "settings/plan.html",
        user=authenticated_user,
        pfp_base64=pfp_base64,
        subscription=subscription,
    )


@settings.route("/billing")
@login_required
@check_user_info_complete
@check_verification
def billing():
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    pfp_base64 = load_pfp(authenticated_user.user_info[0].pfp_uuid)  # type: ignore

    invoices = get_invoices(authenticated_user)

    return render_template(
        "settings/billing.html",
        user=authenticated_user,
        pfp_base64=pfp_base64,
        invoices=invoices,
    )


@settings.route("/change-password", methods=["POST"])
@login_required
@check_user_info_complete
@check_verification
@fresh_login_required
def change_password():
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    current_password = request.form.get("current-password")
    new_password = request.form.get("new-password")
    confirm_password = request.form.get("confirm-password")

    if not isinstance(authenticated_user, UserRegular):
        status = Status(StatusType.ERROR, "Cannot change password for oauth users.").get_status()
        return redirect(url_for("settings.security", _external=False, **status))

    if not current_password or not new_password or not confirm_password:
        status = Status(StatusType.ERROR, "Please fill out all fields.").get_status()
        return redirect(url_for("settings.security", _external=False, **status))

    if not authenticated_user.verify_password(current_password):
        status = Status(StatusType.ERROR, "Incorrect password.").get_status()
        return redirect(url_for("settings.security", _external=False, **status))

    if new_password != confirm_password:
        status = Status(StatusType.ERROR, "Passwords do not match.").get_status()
        return redirect(url_for("settings.security", _external=False, **status))

    authenticated_user.password = new_password
    db.session.commit()
    status = Status(StatusType.SUCCESS, "Password successfully changed.").get_status()

    return redirect(url_for("settings.security", _external=False, **status))


@settings.post("/personal-info")
@login_required
@check_user_info_complete
@check_verification
@fresh_login_required
def change_personal_info():  # noqa
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    first_name = request.form.get("first-name")
    last_name = request.form.get("last-name")
    email = request.form.get("email")
    username = request.form.get("username")
    bio = request.form.get("bio")
    language = request.form.get("language")

    user_info = authenticated_user.user_info[0]  # type: ignore
    if first_name and first_name.strip() != user_info.first_name:
        if first_name == " ":
            status = Status(StatusType.ERROR, "First name cannot be empty.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.first_name = first_name.strip()

    if last_name and last_name.strip() != user_info.last_name:
        if last_name == " ":
            status = Status(StatusType.ERROR, "Last name cannot be empty.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.last_name = last_name.strip()

    if email and email != authenticated_user.email:
        if email == " ":
            status = Status(StatusType.ERROR, "Email cannot be empty.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            status = Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status()
            return redirect(url_for("auth.register", _external=False, **status))

        if isinstance(authenticated_user, UserOauth):
            status = Status(StatusType.ERROR, "Cannot change email for oauth users.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))

        authenticated_user.email = email

    if bio and bio.strip() != user_info.bio:
        if bio == " ":
            status = Status(StatusType.ERROR, "Bio cannot be empty.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.bio = bio.strip()

    if username and username.strip() != user_info.username:
        if username == " ":
            status = Status(StatusType.ERROR, "Username cannot be empty.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        if UserInfo.is_taken(username):
            status = Status(StatusType.ERROR, "Username is taken.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))

        user_info.username = username.strip()

    if language and language != user_info.language:
        if language == " ":
            status = Status(StatusType.ERROR, "Language cannot be empty.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        if language not in language_list:
            status = Status(StatusType.ERROR, "Invalid language.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))

        user_info.language = language

    db.session.commit()

    status = Status(StatusType.SUCCESS, "Personal info successfully changed.").get_status()
    return redirect(url_for("settings.index", _external=False, **status))


@settings.route("/delete-account", methods=["GET", "POST"])
@login_required
@check_user_info_complete
@check_verification
@fresh_login_required
def delete_account():
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    if request.method == "POST":
        db.session.delete(authenticated_user)
        db.session.commit()
        logout_user()

        return redirect(url_for("main.index", _external=False))

    if isinstance(authenticated_user, UserOauth):
        return render_template("settings/delete_oauth_account.html")

    return render_template("settings/delete_account.html")
