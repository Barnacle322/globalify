"""Auth blueprint — magic-link (passwordless) email login.

Flow:
  POST /login  → find-or-create User; issue LoginToken; stub-email the link.
  GET  /auth/verify?token=…  → verify+consume token; login_user; redirect.
  GET  /logout → logout_user; redirect to home.

OAuth routes have been removed (Phase 2e).
The old email-verification-code flow (EmailVerification, /verify-email,
/resend-verification, /email-verification, /fetch-time) is preserved because
the decorators.check_verification guard and claim.py still reference
auth.email_verification_required.  Magic-link click sets is_verified=True,
so new users will never hit those routes; they exist only for any previously
verified account that pre-dates this migration.
"""

import datetime
from urllib.parse import urlparse

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

from ..extensions import db, login_manager
from ..models import (
    EmailVerification,
    LoginToken,
    User,
    UserInfo,
    UserPayment,
)
from ..utils.decorators import check_user_info_complete
from ..utils.email import send_magic_link
from ..utils.enums import Status, StatusType
from ..utils.errors.error_messages import ACCOUNT_NOT_FOUND

auth = Blueprint("auth", __name__)


def _is_safe_next(target: str | None) -> bool:
    """Return True only for same-host relative paths (no scheme, no netloc)."""
    if not target:
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc and target.startswith("/") and not target.startswith("//")


@login_manager.user_loader
def load_user(user_id: int) -> User | None:
    user = User.get_by_id(id=int(user_id))
    if user:
        return user
    return None


# ---------------------------------------------------------------------------
# Magic-link auth
# ---------------------------------------------------------------------------


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("public.investors"))

    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()

        if not email:
            status = Status(StatusType.ERROR, "Please enter your email address.").get_status()
            return redirect(url_for("auth.login", _external=False, **status))

        # Find-or-create the User by email.
        # Decision: create the User row immediately so the FK on LoginToken is
        # non-nullable.  is_verified is set False here; the magic-link click
        # sets it True — the click IS the verification proof.
        user = User.get_by_email(email)
        if user is None:
            user = User(email=email, is_verified=False)
            db.session.add(user)
            db.session.flush()
            # Create companion UserInfo (required by check_user_info_complete decorator).
            user_info = UserInfo(
                first_name=None,
                last_name=None,
                username=None,
                is_complete=False,
                user=user,
            )
            db.session.add(user_info)
            # Create companion UserPayment so navbar tier deref never 500s.
            db.session.add(UserPayment(user=user))
            db.session.commit()

        # TODO(phase-3): Cap captcha verify here before issuing the token.
        raw = LoginToken.issue(user, "login", ttl_minutes=30)

        link = url_for("auth.verify_magic_link", token=raw, _external=True)
        send_magic_link(email, link)

        status = Status(StatusType.SUCCESS, "Check your email for a login link.").get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    return render_template("auth/login.html", status_type=status_type, msg=msg)


@auth.get("/auth/verify")
def verify_magic_link():
    raw_token = request.args.get("token", "")

    if not raw_token:
        status = Status(StatusType.ERROR, "Missing login token.").get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    user = LoginToken.verify_and_consume(raw_token, "login")

    if user is None:
        status = Status(StatusType.ERROR, "This login link is invalid or has already expired.").get_status()
        return redirect(url_for("auth.login", _external=False, **status))

    # Magic-link click IS the email verification.
    if not user.is_verified:
        user.is_verified = True
        db.session.commit()

    login_user(user)

    next_url = request.args.get("next")
    status = Status(StatusType.SUCCESS, "Welcome! You are now logged in.").get_status()
    if _is_safe_next(next_url):
        return redirect(next_url)
    return redirect(url_for("public.investors", _external=False, **status))


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


# ---------------------------------------------------------------------------
# Username check (used by settings)
# ---------------------------------------------------------------------------


@auth.get("/username/<username>")
@login_required
def username(username: str):
    from ..models import UserInfo

    return jsonify({"is_taken": UserInfo.is_taken(username)})


# ---------------------------------------------------------------------------
# Legacy email-verification-code flow
# (kept so check_verification decorator and claim flow don't break;
#  new magic-link users bypass these entirely because is_verified=True after click)
# ---------------------------------------------------------------------------


@auth.route("/fetch-time/<int:user_id>", methods=["GET"])
@login_required
@check_user_info_complete
def fetch_time(user_id):
    if not user_id:
        return jsonify({"error": "User ID is required"})

    email_verification = EmailVerification.get_last_unused_by_user_id(user_id)
    if email_verification and not email_verification.is_resendable:
        created_at = email_verification.created_at.replace(tzinfo=datetime.UTC, microsecond=0)
        utc_now = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
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
        status = Status(StatusType.ERROR, "The code you have entered is invalid").get_status()
        return redirect(url_for("auth.email_verification_required", next=next_url, _external=False, **status))

    if email_verification.is_expired:
        status = Status(StatusType.ERROR, "The code has already expired!").get_status()
        return redirect(url_for("auth.email_verification_required", next=next_url, _external=False, **status))

    current_user.is_verified = True
    email_verification.is_used = True
    db.session.commit()

    return redirect(url_for("public.investors", next=next_url))


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
        return redirect(url_for("public.investors", _external=False))

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
    status = Status(StatusType.SUCCESS, "Verification code sent! Please check your email.").get_status()
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
        return redirect(url_for("public.investors", next=next_url))

    return render_template("verify_email.html", user_id=current_user.id, status_type=status_type, msg=msg)
