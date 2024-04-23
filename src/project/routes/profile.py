from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..models import Company, User
from .main import check_verification

profile = Blueprint("profile", __name__)


@profile.route("/user/<int:user_id>/", methods=["GET"])
@login_required
@check_verification
def user_profile(user_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user = User.get_by_id(user_id)
    if not user:
        return redirect(url_for("main.search"))

    company = Company.get_by_user_id(user_id)
    if not company:
        return redirect(url_for("main.search"))

    return render_template(
        "user_profile.html",
        user=user,
        authenticated_user=authenticated_user,
        company=company,
    )
