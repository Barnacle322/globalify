from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import aliased

from ..extensions import db
from ..models import Company, Country, Industry, Investor, Round, User, UserCompany, UserInfo
from .main import check_verification

profile = Blueprint("profile", __name__)


@profile.route("/<username>", methods=["GET"])
@login_required
@check_verification
def user_profile(username):
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_company_alias = aliased(UserCompany)

    data = db.session.execute(
        db.select(UserInfo, User, Company, Round, Industry, Country)
        .select_from(UserInfo)
        .outerjoin(User, User.id == UserInfo.user_id)
        .outerjoin(user_company_alias, user_company_alias.user_id == User.id)
        .outerjoin(Company, Company.id == user_company_alias.company_id)
        .outerjoin(Industry, Industry.id == Company.industry_id)
        .outerjoin(Round, Round.id == Company.preferred_round_id)
        .outerjoin(Country, Country.id == Company.country_id)
        .where(UserInfo.username == username, user_company_alias.is_public, User.id == UserInfo.user_id)
    ).all()

    print("\n\n\n\n\n\n\n")
    print(data)

    if len(data) == 0:
        return redirect(url_for("main.search"))

    investor = Investor.get_by_user_id(authenticated_user.id)

    return render_template(
        "user_profile.html",
        user_info=data[0][0],
        user=data[0][1],
        company=data[0][2],
        authenticated_user=authenticated_user,
        investor=investor,
    )
