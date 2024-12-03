from flask import (
    Blueprint,
    jsonify,
    request,
)
from flask_login import login_required

from ..extensions import db
from ..models import (
    FundingRound,
    Investment,
)
from ..schemas.investment import FetchFundingRoundSchema, FullInvestmentSchema
from ..utils.decorators import check_user_info_complete, check_verification

investment = Blueprint("investment", __name__)


@investment.get("/funding-round/<int:round_id>")
@login_required
@check_user_info_complete
@check_verification
def get_funding_round(round_id):
    model_funding_round = FundingRound.get_by_id(round_id)

    if not model_funding_round:
        return jsonify({"status": "error", "message": "Funding Round not found."}), 404

    funding_round = FetchFundingRoundSchema(
        id=model_funding_round.id,
        company_id=model_funding_round.company.id,
        round_id=model_funding_round.round.id,
        announced_date=model_funding_round.announced_date,
    ).model_dump()

    return jsonify({"funding_round": funding_round})


@investment.get("/investment/<int:investment_id>")
@login_required
@check_user_info_complete
@check_verification
def get_investment(investment_id):
    model_investment = Investment.get_by_id(investment_id)

    if not model_investment:
        return jsonify({"status": "error", "message": "Investment not found."}), 404

    investment = FullInvestmentSchema(
        id=model_investment.id,
        funding_round_id=model_investment.funding_round_id,
        investor_id=model_investment.investor_id,
        investment_firm_id=model_investment.investment_firm_id,
        amount=model_investment.amount,
        created_by_admin=model_investment.created_by_admin,
        is_verified=model_investment.is_verified,
    ).model_dump()

    return jsonify({"investment": investment})


@investment.post("/investment/create")
@login_required
@check_user_info_complete
@check_verification
def create_investment():
    form_data = request.get_json()

    investor_id = form_data.get("investor_id")
    investment_firm_id = form_data.get("investment_firm_id")
    amount = form_data.get("amount")
    funding_round_id = form_data.get("funding_round_id")
    created_by_admin = form_data.get("created_by_admin")
    is_verified = form_data.get("is_verified")

    created_by_admin = True if created_by_admin == "True" else False

    new_investment = Investment(
        investor_id=investor_id,
        investment_firm_id=investment_firm_id,
        funding_round_id=funding_round_id,
        amount=amount,
        created_by_admin=created_by_admin,
        is_verified=is_verified,
    )

    try:
        db.session.add(new_investment)
        db.session.commit()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "success"}), 200


@investment.post("/investment/<int:investment_id>/update")
@login_required
@check_user_info_complete
@check_verification
def update_investment(investment_id):
    form_data = request.get_json()

    investment = Investment.get_by_id(investment_id)
    if not investment:
        return jsonify({"status": "error", "message": "Investment not found."}), 404

    investor_id = form_data.get("investor_id")
    investment_firm_id = form_data.get("investment_firm_id")
    amount = form_data.get("amount")
    funding_round_id = form_data.get("funding_round_id")
    created_by_admin = form_data.get("created_by_admin")
    is_verified = form_data.get("is_verified")

    created_by_admin = True if created_by_admin == "True" else False

    investment.investor_id = investor_id
    investment.investment_firm_id = investment_firm_id
    investment.amount = amount
    investment.funding_round_id = funding_round_id
    investment.created_by_admin = created_by_admin
    investment.is_verified = is_verified

    db.session.commit()

    return jsonify({"status": "success"}), 200


@investment.post("/investment/<int:investment_id>/delete")
@login_required
@check_user_info_complete
@check_verification
def delete_investment(investment_id):
    investment = Investment.get_by_id(investment_id)
    if not investment:
        return jsonify({"status": "error", "message": "Investment not found."}), 404

    db.session.delete(investment)
    db.session.commit()

    return jsonify({"status": "success"}), 200
