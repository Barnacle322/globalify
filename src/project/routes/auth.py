import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
    logout_user,
)

from ..extensions import db, login_manager
from ..models import (
    EmailVerification,
    User,
    UserInfo,
)
from ..utils.decorators import check_user_info_complete
from ..utils.enums import Status, StatusType
from ..utils.errors.error_messages import ACCOUNT_NOT_FOUND

auth = Blueprint("auth", __name__)


@login_manager.user_loader
def load_user(user_id: int) -> User | None:
    user = User.get_by_id(id=int(user_id))
    if user:
        return user
    return None


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
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    token = request.args.get("uuid", "")
    next_url = request.args.get("next")
    email_verification = EmailVerification.get_by_token(token)
    user = User.get_by_id(email_verification.user_id) if email_verification else None

    if not email_verification or not user or user.id != current_user.id:
        statuc = Status(StatusType.ERROR, "The code you have entered is invalid").get_status()
        return redirect(url_for("auth.email_verification_required", next=next_url, _external=False, **statuc))

    if email_verification.is_expired:
        status = Status(StatusType.ERROR, "The code has already expired!").get_status()
        return redirect(url_for("auth.email_verification_required", next=next_url, _external=False, **status))

    current_user.is_verified = True
    email_verification.is_used = True
    db.session.commit()

    return redirect(url_for("search.investor_search", next=next_url))


@auth.route("/resend-verification/<int:user_id>")
@login_required
@check_user_info_complete
def resend_verification_email(user_id):
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    user = User.get_by_id(user_id)

    if not user or user.id != current_user.id:
        status = Status(StatusType.ERROR, ACCOUNT_NOT_FOUND).get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    if user.is_verified:
        return redirect(url_for("search.investor_search", _external=False))

    last_verification = EmailVerification.get_last_unused_by_user_id(user_id)

    if last_verification:
        if not last_verification.is_resendable:
            status = Status(StatusType.WARNING, "You can only request a new code once per minute.").get_status()
            return redirect(url_for("auth.email_verification_required", _external=False, **status))

    EmailVerification.expire_all_by_user_id(user_id)

    verification = EmailVerification(user_id=user_id)
    db.session.add(verification)
    db.session.commit()

    # TODO Phase 3: send verification email via magic-link service

    status = Status(
        StatusType.SUCCESS,
        "Verification code sent! Please check your email.",
    ).get_status()
    return redirect(url_for("auth.email_verification_required", _external=False, **status))


@auth.route("/email-verification", methods=["GET", "POST"])
@login_required
@check_user_info_complete
def email_verification_required():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    next_url = request.args.get("next")

    if current_user.is_verified:
        return redirect(url_for("search.investor_search", next=next_url))

    return render_template("verify_email.html", user_id=current_user.id, status_type=status_type, msg=msg)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("search.investor_search"))

    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template("auth/login.html", status_type=status_type, msg=msg)


@auth.get("/username/<username>")
@login_required
def username(username: str):
    return jsonify({"is_taken": UserInfo.is_taken(username)})


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))
