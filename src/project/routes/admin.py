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
from ..utils.enums import NotificationDestination, Status, StatusType
from ..utils.errors.error_messages import NOT_AUTHORIZED
from ..utils.suggestion import WEIGHTS, check_weights

admin = Blueprint("admin", __name__)


@admin.route("/dashboard")
def admin_investor_view():
    investors = Investor.get_all()

    return render_template("admin/investor.html", investors=investors)


@admin.route("/dashboard/investor/<int:id>")
def edit_investor_view(id):
    investor = Investor.get_by_id(id)

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template("admin/edit_investor.html", investor=investor, rounds=rounds, industries=industries)


@admin.route("/dashboard/investor/<int:id>", methods=["POST"])
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

    return redirect("/admin/dashboard", code=302)
