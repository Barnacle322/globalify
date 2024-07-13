from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Company, Investor, User, UserCompany, UserInfo
from .main import check_verification

profile = Blueprint("profile", __name__)


@profile.route("/<username>", methods=["GET"])
@login_required
@check_verification
def user_profile(username):
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_info = UserInfo.get_by_username(username)
    if not user_info:
        return redirect(url_for("main.search"))

    companies = db.session.scalars(
        db.select(UserCompany, Company)
        .options(joinedload(Company.preferred_round), joinedload(Company.industry), joinedload(Company.country))
        .join(Company)
        .where(UserCompany.user_id == user_info.user_id, UserCompany.is_public.is_(True))
        .order_by(UserCompany.is_primary.desc())
    )

    investor = Investor.get_by_user_id(authenticated_user.id)

    return render_template(
        "user_profile.html",
        user_info=user_info,
        user=authenticated_user,
        companies=companies,
        authenticated_user=authenticated_user,
        investor=investor,
    )
