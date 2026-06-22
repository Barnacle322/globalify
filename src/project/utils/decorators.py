from functools import wraps

from flask import redirect, request, url_for
from flask_login import current_user

from ..models import User


def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not isinstance(current_user, User):
            return redirect(url_for("auth.login"))
        if not current_user.is_authenticated:
            return redirect("/login", code=302)
        if not current_user.is_admin:
            return redirect("/", code=302)
        return func(*args, **kwargs)

    return decorated_function


def check_user_info_complete(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        # onboarding flow removed in the pivot; info-completeness no longer gates access
        if not isinstance(current_user, User):
            return redirect(url_for("auth.login"))
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return func(*args, **kwargs)

    return decorated_function


def check_verification(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        next_url = request.args.get("next")
        if not isinstance(current_user, User):
            return redirect(url_for("auth.login"))
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        elif not current_user.is_verified:
            return redirect(url_for("auth.email_verification_required", next=next_url))
        return func(*args, **kwargs)

    return decorated_function
