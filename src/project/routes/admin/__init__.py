from datetime import UTC, datetime

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from src.project.utils.errors.error_messages import INVALID_CLAIM_REQUEST, INVESTOR_NOT_FOUND, NO_CLAIM_REQUEST

from ...extensions import db
from ...models import (
    ClaimRequest,
    Industry,
    Investor,
    NotableInvestment,
    User,
)
from ...utils.decorators import admin_only
from ...utils.enums import (
    RequestStatus,
    Status,
    StatusType,
)
from .company import company as company_blueprint
from .investment_firm import investment_firm as investment_firm_blueprint
from .investor import investor as investor_blueprint

admin = Blueprint("admin", __name__)
admin.register_blueprint(investor_blueprint, url_prefix="/investors")
admin.register_blueprint(investment_firm_blueprint, url_prefix="/investment-firms")
admin.register_blueprint(company_blueprint, url_prefix="/companies")


@admin.get("/users/search/<search_input>")
@admin_only
def search_user(search_input):
    users = db.session.execute(select(User).where(User.email.contains(search_input))).scalars().all()

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
    claim_requests = ClaimRequest.get_all()

    return render_template("admin/claim_requests.html", claim_requests=claim_requests)


@admin.post("/claim-request/<int:id>")
@admin_only
def edit_claim_request(id):
    claim_request = ClaimRequest.get_by_id(id)

    if not claim_request:
        status = Status(StatusType.ERROR, NO_CLAIM_REQUEST).get_status()
        return redirect(url_for("admin.claim_requests_view", _external=True, **status))

    investor = Investor.get_by_id(claim_request.investor_id)
    if not investor:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.claim_requests_view", _external=True, **status))

    form_data = request.get_json()
    claim_status = form_data.get("status")

    if claim_status not in ["approved", "rejected"]:
        status = Status(StatusType.ERROR, INVALID_CLAIM_REQUEST).get_status()
        return redirect(url_for("admin.claim_requests_view", _external=True, **status))
    elif claim_status == "approved":
        claim_request.status = RequestStatus.APPROVED
        claim_request.approved_at = datetime.now(UTC)
        claim_request.approved_by = current_user.user_info.username
        investor.user = claim_request.user
    elif claim_status == "rejected":
        claim_request.status = RequestStatus.REJECTED
        investor.user = None
    db.session.commit()

    return jsonify({"message": "Claim request updated"}), 200
