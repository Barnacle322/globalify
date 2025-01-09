from datetime import UTC, datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from ...extensions import db
from ...models import (
    ClaimRequest,
    Company,
    Industry,
    Investor,
    NotableInvestment,
    User,
    UserCompany,
)
from ...utils.decorators import admin_only
from ...utils.enums import (
    CompanyRole,
    RequestStatus,
    Status,
    StatusType,
)
from ...utils.errors.error_messages import (
    INVALID_CLAIM_REQUEST,
    INVESTOR_NOT_FOUND,
    NO_CLAIM_REQUEST,
    USER_ALREADY_IN_COMPANY,
)
from .company import company as company_blueprint
from .funding_round import funding_round as funding_round_blueprint
from .investment_firm import investment_firm as investment_firm_blueprint
from .investments import investment as investment_blueprint
from .investor import investor as investor_blueprint
from .user import user as user_blueprint

admin = Blueprint("admin", __name__)
admin.register_blueprint(investor_blueprint, url_prefix="/investors")
admin.register_blueprint(investment_firm_blueprint, url_prefix="/investment-firms")
admin.register_blueprint(company_blueprint, url_prefix="/companies")
admin.register_blueprint(funding_round_blueprint, url_prefix="/funding-rounds")
admin.register_blueprint(user_blueprint, url_prefix="/users")
admin.register_blueprint(investment_blueprint, url_prefix="/investments")


@admin.get("/users/search/<search_input>")
@admin_only
def search_user(search_input):
    users = db.session.scalars(select(User).where(User.email.contains(search_input))).unique().all()

    return jsonify(users=[user.email for user in users])


@admin.get("/search_industries/<search_input>")
@admin_only
def search_industry(search_input):
    industries = db.session.execute(select(Industry).where(Industry.name.contains(search_input))).scalars().all()

    return jsonify(industries=[industry.name for industry in industries])


@admin.get("/search_notable_investments/<search_input>")
@admin_only
def search_notable_investment(search_input):
    notable_investments = (
        db.session.execute(select(NotableInvestment).where(NotableInvestment.name.contains(search_input)))
        .scalars()
        .all()
    )

    return jsonify(notable_investments=[notable_investment.name for notable_investment in notable_investments])


@admin.get("/claim-requests")
@admin_only
def claim_requests_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    claim_requests = ClaimRequest.get_all_for_investors()

    return render_template("admin/claim_requests.html", claim_requests=claim_requests, status_type=status_type, msg=msg)


@admin.get("/claim-company-requests")
@admin_only
def claim_company_requests_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    claim_requests = ClaimRequest.get_all_for_companies()

    return render_template(
        "admin/claim_company_requests.html",
        claim_requests=claim_requests,
        status_type=status_type,
        msg=msg,
    )


@admin.post("/claim-request/<int:id>")
@admin_only
def edit_claim_request(id):
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    claim_request = ClaimRequest.get_by_id(id)

    if not claim_request:
        status = Status(StatusType.ERROR, NO_CLAIM_REQUEST).get_status()
        return redirect(url_for("admin.claim_requests_view", _external=True, **status))

    claiming_user = User.get_by_id(claim_request.user_id)
    if not claiming_user:
        status = Status(StatusType.ERROR, "User not found").get_status()
        return redirect(url_for("admin.claim_requests_view", _external=True, **status))

    investor = Investor.get_by_id(claim_request.investor_id)
    if not investor:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.claim_requests_view", _external=True, **status))

    form_data = request.get_json()
    claim_status = form_data.get("status")

    if claim_status not in [RequestStatus.APPROVED.value, RequestStatus.REJECTED.value]:
        status = Status(StatusType.ERROR, INVALID_CLAIM_REQUEST).get_status()
        return redirect(url_for("admin.claim_requests_view", _external=True, **status))
    elif claim_status == RequestStatus.APPROVED.value:
        claim_request.status = RequestStatus.APPROVED
        claim_request.approved_at = datetime.now(UTC)
        claim_request.approved_by = current_user.id
        investor.user = claim_request.user

        if not claiming_user.user_info.first_name:
            claiming_user.user_info.first_name = investor.first_name
        if not claiming_user.user_info.last_name:
            claiming_user.user_info.last_name = investor.last_name
        if not claiming_user.user_info.username:
            claiming_user.user_info.set_username()
        if not claiming_user.user_info.is_complete:
            claiming_user.user_info.is_complete = True

    elif claim_status == RequestStatus.REJECTED.value:
        claim_request.status = RequestStatus.REJECTED
        investor.user = None
    db.session.commit()

    return jsonify({"message": "Claim request updated"}), 200


@admin.post("/claim-company-request/<int:id>")
@admin_only
def edit_claim_company_request(id):
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    claim_request = ClaimRequest.get_by_id(id)

    if not claim_request:
        status = Status(StatusType.ERROR, NO_CLAIM_REQUEST).get_status()
        return redirect(url_for("admin.claim_company_requests_view", _external=False, **status))

    claiming_user = User.get_by_id(claim_request.user_id)
    if not claiming_user:
        status = Status(StatusType.ERROR, "User not found").get_status()
        return redirect(url_for("admin.claim_company_requests_view", _external=False, **status))

    company = Company.get_by_id(claim_request.company_id)
    if not company:
        status = Status(StatusType.ERROR, "Company not found.").get_status()
        return redirect(url_for("admin.claim_company_requests_view", _external=False, **status))

    form_data = request.get_json()
    claim_status = form_data.get("status")

    if claim_status not in [RequestStatus.APPROVED.value, RequestStatus.REJECTED.value]:
        status = Status(StatusType.ERROR, INVALID_CLAIM_REQUEST).get_status()
        return redirect(url_for("admin.claim_company_requests_view", _external=True, **status))
    elif claim_status == RequestStatus.APPROVED.value:
        claim_request.status = RequestStatus.APPROVED
        claim_request.approved_at = datetime.now(UTC)
        claim_request.approved_by = current_user.id

        existing_user_company = UserCompany.get_by_user_and_company_id(claiming_user.id, company.id)
        if existing_user_company:
            status = Status(StatusType.ERROR, USER_ALREADY_IN_COMPANY).get_status()
            return redirect(url_for("admin.claim_company_requests_view", _external=False, **status))

        existing_user_companies = UserCompany.get_by_user_id(user_id=current_user.id)
        is_primary = not existing_user_companies

        user_company = UserCompany(
            user_id=claiming_user.id,
            company_id=company.id,
            position=CompanyRole.TEAM.value,
            is_primary=is_primary,
        )
        db.session.add(user_company)

        if not claiming_user.user_info.username:
            claiming_user.user_info.set_username()
        if not claiming_user.user_info.is_complete:
            claiming_user.user_info.is_complete = True

    elif claim_status == RequestStatus.REJECTED.value:
        claim_request.status = RequestStatus.REJECTED

    db.session.commit()

    return jsonify({"message": "Claim request updated"}), 200


@admin.post("/create/notable-investment")
@admin_only
def create_notable_investment():
    form_data = request.get_json()
    name = form_data.get("name")

    if not name:
        status = Status(StatusType.ERROR, "Name and description are required").get_status()
        return redirect(url_for("admin.investment_firm_view", _external=True, **status))

    notable_investment = NotableInvestment(name=name)
    db.session.add(notable_investment)
    db.session.commit()

    notable_investment_dict = {"name": notable_investment.name}
    return jsonify({"notable_investment": notable_investment_dict}), 200
