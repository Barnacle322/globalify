import re
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    Company,
    Industry,
    InvestmentFirm,
    Investor,
    Round,
)
from ..utils.errors.error_messages import NOT_AUTHORIZED
from ..utils.suggestion import WEIGHTS, check_weights

admin = Blueprint("admin", __name__)


@admin.route("/investors")
def admin_investor_view():
    investors = Investor.get_all()

    return render_template("admin/investors.html", investors=investors)


@admin.route("/investor/<int:id>")
def edit_investor_view(id):
    investor = Investor.get_by_id(id)

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template("admin/edit_investor.html", investor=investor, rounds=rounds, industries=industries)


@admin.route("/investor/<int:id>", methods=["POST"])
def update_investor(id):
    data = request.get_json()

    investor = Investor.get_by_id(id)

    if not investor:
        return jsonify({"message": "Investor not found"}), 404

    first_name = data.get("first_name", investor.first_name)
    last_name = data.get("last_name", investor.last_name)
    firm_name = data.get("firm_name", investor.firm_name)
    about = data.get("about", investor.about)
    website = data.get("website", investor.website)
    linkedin = data.get("linkedin", investor.linkedin)
    twitter = data.get("twitter", investor.twitter)
    email = data.get("email", investor.email)
    phone_number = data.get("phone_number", investor.phone_number)
    n_investments = data.get("n_investments", investor.n_investments)
    n_exits = data.get("n_exits", investor.n_exits)
    min_investment = data.get("min_investment", investor.min_investment)
    max_investment = data.get("max_investment", investor.max_investment)
    location = data.get("location", investor.location)
    selected_round_ids = data.get("round", investor.rounds)
    selected_industry_ids = data.get("industry", investor.industries)

    investor.first_name = first_name
    investor.last_name = last_name
    investor.firm_name = firm_name
    investor.about = about
    investor.website = website
    investor.linkedin = linkedin
    investor.twitter = twitter
    investor.email = email
    investor.phone_number = phone_number
    investor.n_investments = n_investments
    investor.n_exits = n_exits
    investor.min_investment = min_investment
    investor.max_investment = max_investment
    investor.location = location
    investor.rounds = list(Round.get_by_id_list(selected_round_ids))
    investor.industries = list(Industry.get_by_id_list(selected_industry_ids))

    db.session.commit()

    return redirect("/admin/investors", code=302)


@admin.route("/investor/<int:id>/delete", methods=["POST"])
def delete_investor(id):
    investor = Investor.get_by_id(id)

    if not investor:
        return jsonify({"message": "Investor not found"}), 404

    db.session.delete(investor)
    db.session.commit()

    return redirect("/admin", code=302)


@admin.route("/investment-firms")
def admin_investment_firm_view():
    investment_firms = InvestmentFirm.get_all()

    return render_template("admin/investment_firms.html", investment_firms=investment_firms)


@admin.route("/investment-firm/<int:id>")
def edit_investment_firm_view(id):
    investment_firm = InvestmentFirm.get_by_id(id)

    return render_template("admin/edit_investment_firm.html", investment_firm=investment_firm)


@admin.route("/investment-firm/<int:id>", methods=["POST"])
def update_investment_firm(id):
    data = request.get_json()

    investment_firm = InvestmentFirm.get_by_id(id)

    if not investment_firm:
        return jsonify({"message": "Investment Firm not found"}), 404

    name = data.get("name", investment_firm.name)
    about = data.get("about", investment_firm.about)
    website = data.get("website", investment_firm.website)
    email = data.get("email", investment_firm.email)
    phone_number = data.get("phone_number", investment_firm.phone_number)
    n_investments = data.get("n_investments", investment_firm.n_investments)
    n_exits = data.get("n_exits", investment_firm.n_exits)
    n_employees = data.get("n_employees", investment_firm.n_employees)
    min_investment = data.get("min_investment", investment_firm.min_investment)
    max_investment = data.get("max_investment", investment_firm.max_investment)
    location = data.get("location", investment_firm.location)

    investment_firm.name = name
    investment_firm.about = about
    investment_firm.website = website
    investment_firm.email = email
    investment_firm.phone_number = phone_number
    investment_firm.n_investments = n_investments
    investment_firm.n_exits = n_exits
    investment_firm.n_employees = n_employees
    investment_firm.min_investment = min_investment
    investment_firm.max_investment = max_investment
    investment_firm.location = location

    db.session.commit()

    return redirect("/admin/investment-firms", code=302)
