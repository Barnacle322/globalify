import base64

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import (
    AnonymousUserMixin,
    current_user,
    fresh_login_required,
    login_required,
)

from ..extensions import db
from ..models import User, UserPayment
from ..utils.google_storage import download_blob_into_memory
from ..utils.info_lists import languages as LANGUAGE_LIST
from ..utils.status_enum import Status, StatusType
from .main import check_user_info_complete, check_verification
from .payment import get_invoices

settings = Blueprint("settings", __name__)


@settings.route("/")
@settings.route("/general")
@login_required
@check_user_info_complete
@check_verification
def index():
    authenticated_user: User = current_user  # type: ignore
    if isinstance(authenticated_user, AnonymousUserMixin):
        return redirect(url_for("auth.login"))

    pfp_base64 = False
    try:
        if pfp_uuid := authenticated_user.user_info[0].pfp_uuid:
            pfp = download_blob_into_memory(pfp_uuid)  # type: ignore
            pfp_base64 = base64.b64encode(pfp).decode("utf-8")
    except Exception as e:
        print(e)

    return render_template(
        "settings/general.html",
        user=authenticated_user,
        pfp_base64=pfp_base64,
        languages=LANGUAGE_LIST,
    )


@settings.route("/security")
@login_required
@check_user_info_complete
@check_verification
def security():
    authenticated_user: User = current_user  # type: ignore
    if isinstance(authenticated_user, AnonymousUserMixin):
        return redirect(url_for("auth.login"))

    pfp_base64 = False
    try:
        if pfp_uuid := authenticated_user.user_info[0].pfp_uuid:
            pfp = download_blob_into_memory(pfp_uuid)  # type: ignore
            pfp_base64 = base64.b64encode(pfp).decode("utf-8")
    except Exception as e:
        print(e)

    return render_template(
        "settings/security.html",
        user=authenticated_user,
        pfp_base64=pfp_base64,
    )


@settings.route("/plan")
@login_required
@check_user_info_complete
@check_verification
def plan():
    authenticated_user: User = current_user  # type: ignore
    if isinstance(authenticated_user, AnonymousUserMixin):
        return redirect(url_for("auth.login"))

    pfp_base64 = False
    try:
        if pfp_uuid := authenticated_user.user_info[0].pfp_uuid:
            pfp = download_blob_into_memory(pfp_uuid)  # type: ignore
            pfp_base64 = base64.b64encode(pfp).decode("utf-8")
    except Exception as e:
        print(e)

    user_payment = UserPayment.get_by_user_id(authenticated_user.id)
    subscription = {}
    if user_payment:
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
    authenticated_user: User = current_user  # type: ignore
    if isinstance(authenticated_user, AnonymousUserMixin):
        return redirect(url_for("auth.login"))

    pfp_base64 = False
    try:
        if pfp_uuid := authenticated_user.user_info[0].pfp_uuid:
            pfp = download_blob_into_memory(pfp_uuid)  # type: ignore
            pfp_base64 = base64.b64encode(pfp).decode("utf-8")
    except Exception as e:
        print(e)

    invoices = get_invoices(authenticated_user)
    print(invoices)

    return render_template(
        "settings/billing.html",
        user=authenticated_user,
        pfp_base64=pfp_base64,
        invoices=invoices,
    )


# TODO
@settings.post("/change-password")
@login_required
@check_user_info_complete
@check_verification
@fresh_login_required
def change_password():
    authenticated_user: User = current_user  # type: ignore
    if isinstance(authenticated_user, AnonymousUserMixin):
        return redirect(url_for("auth.login"))

    current_password = request.form.get("current-password")
    new_password = request.form.get("new-password")
    confirm_password = request.form.get("confirm-password")

    if not authenticated_user.verify_password(current_password):
        status = Status(StatusType.ERROR, "Incorrect password.").get_status()
        return redirect(url_for("main.settings", _external=False, **status))

    if new_password != confirm_password:
        status = Status(StatusType.ERROR, "Passwords do not match.").get_status()
        return redirect(url_for("main.settings", _external=False, **status))

    authenticated_user.password = new_password
    db.session.commit()
    status = Status(StatusType.SUCCESS, "Password successfully changed.").get_status()

    return redirect(url_for("main.settings", _external=False, **status))
