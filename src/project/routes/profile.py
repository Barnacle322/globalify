from flask import Blueprint, jsonify, redirect, render_template, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Company, User, UserCompany, UserInfo
from ..schemas.profile import Investor as InvestorSchema
from ..schemas.profile import UserCompany as UserCompanySchema
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


@profile.route("/accounts/get")
@login_required
@check_verification
def get_profile():
    if not isinstance(current_user, User):
        return redirect(url_for("search.investor_search"))

    user_companies = current_user.user_companies
    investor = current_user.investor

    user_companies_object = [
        UserCompanySchema(
            id=user_company.company.id,
            name=user_company.company.name,
            picture_url=user_company.company.picture_url,
            is_primary=user_company.is_primary,
        ).model_dump()
        for user_company in user_companies
    ]

    investor_object = InvestorSchema(
        investor_mode=current_user.is_investor_mode,
        name=investor.full_name if investor else None,
        twitter=investor.twitter if investor else None,
    ).model_dump()

    return jsonify({"user_companies": user_companies_object, "investor": investor_object})


@profile.route("/mode/investor")
@login_required
@check_verification
def change_to_investment_mode():
    if not isinstance(current_user, User):
        return redirect(url_for("search.investor_search"))

    current_user.is_investor_mode = True
    db.session.commit()

    return redirect(url_for("search.search_companies"))


@profile.route("/mode/company/<company_id>")
@login_required
@check_verification
def change_to_company_mode(company_id):
    if not isinstance(current_user, User):
        return redirect(url_for("search.investor_search"))

    current_user.is_investor_mode = False
    db.session.commit()

    user_company = UserCompany.get_by_user_and_company_id(user_id=current_user.id, company_id=company_id)
    if not user_company:
        return redirect(url_for("search.investor_search"))

    user_company.set_primary = current_user.id

    return redirect(url_for("search.investor_search"))
