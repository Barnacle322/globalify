from functools import wraps

from flask import redirect, request, url_for
from flask_login import current_user


def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect("/login", code=302)

        if not current_user.is_admin:
            return redirect("/", code=302)

        return func(*args, **kwargs)

    return decorated_function


def check_user_info_complete(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        next_url = request.args.get("next")
        if not current_user.is_authenticated:  # type: ignore
            return redirect(url_for("auth.login"))
        elif not current_user.user_info.is_complete:  # type: ignore
            return redirect(url_for("onboarding.index", next=next_url))
        return func(*args, **kwargs)

    return decorated_function


def check_verification(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        next_url = request.args.get("next")
        if not current_user.is_authenticated:  # type: ignore
            return redirect(url_for("auth.login"))
        elif not current_user.is_verified:  # type: ignore
            return redirect(url_for("auth.email_verification_required", next=next_url))
        return func(*args, **kwargs)

    return decorated_function
