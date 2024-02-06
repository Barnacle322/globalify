from flask import Blueprint, abort, render_template
from flask_login import current_user, login_required

from ..models import Company, User, UserInfo
from .main import check_verification

profile = Blueprint("profile", __name__)


@profile.route("/user/<int:user_id>/", methods=["GET"])
@login_required
@check_verification
def user_profile(user_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user = User.get_by_id(user_id)
    if not user:
        abort(404)

    user_info = UserInfo.get_by_user_id(user_id)
    if not user_info:
        abort(404)

    if user:
        return render_template(
            "profile/user_profile.html", user=user, user_info=user_info, authenticated_user=authenticated_user
        )
    else:
        abort(404)


@profile.route("/company/<int:user_id>/", methods=["GET", "POST"])
@check_verification
def company(user_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    company = Company.get_by_user_id(user_id)
    if not company:
        abort(404)

    return render_template(
        "profile/company_profile.html",
        company=company,
        user=authenticated_user,
    )
