from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Company, User, UserCompany, UserInfo
from .main import check_verification

profile = Blueprint("profile", __name__)


@profile.route("/<username>", methods=["GET"])
def user_profile(username):
    user_info = UserInfo.get_by_username(username)

    if not user_info:
        return redirect(url_for("search.investor_search"))

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

    description = ""
    if user_info.bio:
        description = user_info.bio[:140]
        if not description.endswith("."):
            description += "."

    company_name_list = tuple(company.company.name for company in companies)
    if company_name_list_len := len(company_name_list) > 0:
        description += f" {user_info.full_name} works at"

        if company_name_list_len == 1:
            description += f" {company_name_list[0]}."
        else:
            for index, company_name in enumerate(company_name_list):
                if index == company_name_list_len - 1:
                    description += f" and {company_name}."
                elif index == company_name_list_len - 2:
                    description += f" {company_name}"
                else:
                    description += f" {company_name},"

    investor = user_info.user.investor
    if investor:
        description += f" {user_info.first_name} is also an investor."

    return render_template(
        "user_profile.html",
        user_info=user_info,
        user=user_info.user,
        current_user=current_user if current_user.is_authenticated else None,
        companies=companies,
        authenticated_user=current_user,
        investor=investor,
        description=description,
    )


@profile.route("/company/<slug>")
@login_required
@check_verification
def company_profile(slug):
    if not isinstance(current_user, User):
        return redirect(url_for("search.investor_search"))

    company = Company.get_by_slug(slug)
    if not company:
        return redirect(url_for("search.investor_search"))

    return render_template(
        "company_profile.html",
        company=company,
        user=current_user,
    )

@profile.route("/change/investment/mode/<int:user_id>")
@login_required
@check_verification
def change_to_investment_mode(user_id):
    if not isinstance(current_user, User):
        return redirect(url_for("search.investor_search"))
    user = User.get_by_id(user_id)
    if user:
        user.is_investor_mode = True
        db.session.commit()
    return redirect(url_for("search.search_companies"))


@profile.route("/change/company/mode/<int:user_id>")
@login_required
@check_verification
def change_to_company_mode(user_id):
    if not isinstance(current_user, User):
        return redirect(url_for("search.investor_search"))
    user = User.get_by_id(user_id)
    if user:
        user.is_investor_mode = False
        db.session.commit()
    return redirect(url_for("search.investor_search"))

