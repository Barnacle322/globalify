from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Company, User, UserCompany, UserInfo
from .main import check_verification

profile = Blueprint("profile", __name__)


@profile.route("/<username>", methods=["GET"])
@login_required
@check_verification
def user_profile(username):
    if not isinstance(current_user, User):
        return redirect(url_for("main.search"))

    user_info = UserInfo.get_by_username(username)
    if not user_info:
        return redirect(url_for("main.search"))

    companies = (
        db.session.scalars(
            db.select(UserCompany, Company)
            .options(joinedload(Company.preferred_round), joinedload(Company.industry), joinedload(Company.country))
            .join(Company)
            .where(UserCompany.user_id == user_info.user_id, UserCompany.is_public.is_(True))
            .order_by(UserCompany.is_primary.desc())
        )
        .unique()
        .all()
    )

    return render_template(
        "user_profile.html",
        user_info=user_info,
        user=user_info.user,
        companies=companies,
        authenticated_user=current_user,
        investor=user_info.user.investor,
    )


@profile.route("/company/<slug>")
@login_required
@check_verification
def company_profile(slug):
    if not isinstance(current_user, User):
        return redirect(url_for("main.search"))

    company = Company.get_by_slug(slug)
    if not company:
        return redirect(url_for("main.search"))

    return render_template(
        "company_profile.html",
        company=company,
        user=current_user,
    )
