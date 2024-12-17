from datetime import datetime

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
from ..schemas.investment import FetchFundingRoundSchema, FullInvestmentSchema, InvestorSchema
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


@investment.post("/funding-round/create")
@login_required
@check_user_info_complete
@check_verification
def create_funding_round():
    form_data = request.get_json()

    company_id = form_data.get("company_id")
    if not company_id:
        return jsonify({"status": "error", "message": "Company ID is required."}), 400

    round_id = form_data.get("round_id") or None
    announced_date = form_data.get("announced_date") or None

    if announced_date:
        announced_date_format = datetime.strptime(announced_date, "%Y-%m-%d")
    else:
        announced_date_format = None

    new_funding_round = FundingRound(
        company_id=company_id,
        custom_company_name=None,
        amount=form_data.get("amount"),
        round_id=round_id,
        announced_date=announced_date_format,
    )

    try:
        db.session.add(new_funding_round)
        db.session.commit()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "success"}), 200


@investment.post("/funding-round/<int:round_id>/update")
@login_required
@check_user_info_complete
@check_verification
def update_funding_round(round_id):
    form_data = request.get_json()

    funding_round = FundingRound.get_by_id(round_id)
    if not funding_round:
        return jsonify({"status": "error", "message": "Funding Round not found."}), 404

    if not form_data.get("company_id"):
        return jsonify({"status": "error", "message": "Company ID is required."}), 400

    funding_round.company_id = form_data.get("company_id", funding_round.company_id)
    funding_round.round_id = form_data.get("round_id", funding_round.round_id) or None
    announced_date_str = form_data.get("announced_date")
    if announced_date_str:
        try:
            funding_round.announced_date = datetime.strptime(announced_date_str, "%Y-%m-%d").date()
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid date format. Use YYYY-MM-DD."}), 400
    else:
        funding_round.announced_date = None
    db.session.commit()

    return jsonify({"status": "success"}), 200


@investment.post("/funding-round/<int:round_id>/delete")
@login_required
@check_user_info_complete
@check_verification
def delete_funding_round(round_id):
    funding_round = FundingRound.get_by_id(round_id)
    if not funding_round:
        return jsonify({"status": "error", "message": "Funding Round not found."}), 404

    db.session.delete(funding_round)
    db.session.commit()

    return jsonify({"status": "success"}), 200


@investment.get("/<int:investment_id>")
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
        investor=InvestorSchema(
            id=model_investment.investor.id,
            name=model_investment.investor.full_name,
        )
        if model_investment.investor
        else None,
        investment_firm=InvestorSchema(
            id=model_investment.investment_firm.id,
            name=model_investment.investment_firm.name,
        )
        if model_investment.investment_firm
        else None,
        custom_name=model_investment.custom_name,
        amount=model_investment.amount,
        date=model_investment.date,
        created_by_admin=model_investment.created_by_admin,
        is_verified=model_investment.is_verified,
    ).model_dump()

    return jsonify({"investment": investment})


@investment.post("/create")
@login_required
@check_user_info_complete
@check_verification
def create_investment():
    form_data = request.get_json()

    created_by_admin = form_data.get("created_by_admin")

    created_by_admin_format = True if created_by_admin == "True" else False

    new_investment = Investment(
        investor_id=form_data.get("investor_id") or None,
        investment_firm_id=form_data.get("investment_firm_id") or None,
        description=form_data.get("description") or None,
        custom_name=form_data.get("custom_name") or None,
        funding_round_id=form_data.get("funding_round_id") or None,
        amount=form_data.get("amount") or None,
        date=datetime.strptime(form_data.get("date"), "%Y-%m-%d"),
        created_by_admin=created_by_admin_format,
        is_verified=form_data.get("is_verified"),
    )

    try:
        db.session.add(new_investment)
        db.session.commit()
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

    return jsonify({"status": "success"}), 200


@investment.post("/<int:investment_id>/update")
@login_required
@check_user_info_complete
@check_verification
def update_investment(investment_id):
    form_data = request.get_json()

    print("\n\n\n\n\n\n\n\n\n\n\n\n")
    print(form_data)

    investment = Investment.get_by_id(investment_id)
    if not investment:
        return jsonify({"status": "error", "message": "Investment not found."}), 404

    investor_id = form_data.get("investor_id", investment.investor_id) or None
    investment_firm_id = form_data.get("investment_firm_id", investment.investment_firm_id) or None
    custom_name = form_data.get("custom_name", investment.custom_name) or None
    amount = form_data.get("amount", investment.amount) or None
    date = datetime.strptime(form_data.get("date", investment.date), "%Y-%m-%d")
    funding_round_id = form_data.get("funding_round_id", investment.funding_round_id) or None
    created_by_admin = form_data.get("created_by_admin", investment.created_by_admin)
    is_verified = form_data.get("is_verified", investment.is_verified)

    created_by_admin = True if created_by_admin == "True" else False

    investment.investor_id = investor_id
    investment.investment_firm_id = investment_firm_id
    investment.custom_name = custom_name
    investment.amount = amount
    investment.date = date
    investment.funding_round_id = funding_round_id
    investment.created_by_admin = created_by_admin
    investment.is_verified = is_verified

    db.session.commit()

    return jsonify({"status": "success"}), 200


@investment.post("/<int:investment_id>/delete")
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
