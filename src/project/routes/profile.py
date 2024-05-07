from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Company, Country, Industry, Round, User, UserInfo
from .main import check_verification

profile = Blueprint("profile", __name__)


@profile.route("/<int:user_id>", methods=["GET"])
@login_required
@check_verification
def user_profile(user_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    data = db.session.execute(
        db.select(UserInfo, Company, Round, Industry, Country)
        .outerjoin(Industry, Industry.id == Company.industry_id)
        .outerjoin(Round, Round.id == Company.preferred_round_id)
        .outerjoin(Country, Country.id == Company.country_id)
        .where(UserInfo.user_id == user_id, Company.user_id == user_id)
    ).all()

    return render_template(
        "user_profile.html",
        user=data[0][0],
        company=data[0][1],
        authenticated_user=authenticated_user,
    )
