from datetime import UTC, datetime
from functools import wraps

from flask import (
    Blueprint,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
)
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import ClaimRequest, Industry, InvestmentFirm, Investor, Round, User
from ..utils.enums import (
    RequestStatus,
)

admin = Blueprint("admin", __name__)


def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect("/login", code=302)

        if not current_user.is_admin:
            return redirect("/", code=302)

        return func(*args, **kwargs)

    return decorated_function


@admin.get("/investors")
@admin_only
def admin_investor_view():
    investors = Investor.get_all()
    return render_template("admin/investors.html", investors=investors)


@admin.get("/investor/<int:id>")
@admin_only
def update_investor_view(id):
    investor = Investor.get_by_id(id)
    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/update_investor.html",
        investor=investor,
        rounds=rounds,
        industries=industries,
    )


@admin.post("/investor/<int:id>")
@admin_only
def update_investor(id):
    form_data = request.get_json()

    investor = Investor.get_by_id(id)
    if not investor:
        abort(404)

    first_name = form_data.get("first_name", investor.first_name)
    last_name = form_data.get("last_name", investor.last_name)
    firm_name = form_data.get("firm_name", investor.firm_name)
    about = form_data.get("about", investor.about)
    location = form_data.get("location", investor.location)

    n_investments = int(form_data.get("n_investments", investor.n_investments) or 0)
    n_exits = int(form_data.get("n_exits", investor.n_exits) or 0)
    min_investment = int(form_data.get("min_investment", investor.min_investment) or 0)
    max_investment = int(form_data.get("max_investment", investor.max_investment) or 0)
    selected_round_ids = form_data.get("round", investor.rounds)
    selected_industry_ids = form_data.get("industry", investor.industries)

    website = form_data.get("website", investor.website)
    linkedin = form_data.get("linkedin", investor.linkedin)
    twitter = form_data.get("twitter", investor.twitter)
    email = form_data.get("email", investor.email)
    phone_number = form_data.get("phone_number", investor.phone_number)

    user_email = form_data.get("user_email")
    user = User.get_by_email(user_email)

    if not all(
        first_name,
        last_name,
        firm_name,
        about,
        email,
        phone_number,
        n_investments,
        n_exits,
        min_investment,
        max_investment,
        location,
        selected_round_ids,
        selected_industry_ids,
    ):
        status = ...
        return redirect(f"/admin/investor/{id}", code=302)

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


@admin.get("/investor/create")
@admin_only
def create_investor_view():
    return render_template("admin/create_investor.html", rounds=Round.get_all(), industries=Industry.get_all())


@admin.post("/investor/create")
@admin_only
def create_investor():
    form_data = request.get_json()

    first_name = form_data.get("first_name")
    last_name = form_data.get("last_name")
    firm_name = form_data.get("firm_name")
    about = form_data.get("about")
    website = form_data.get("website")
    linkedin = form_data.get("linkedin")
    twitter = form_data.get("twitter")
    email = form_data.get("email")
    phone_number = form_data.get("phone_number")
    n_investments = int(form_data.get("n_investments") or 0)
    n_exits = int(form_data.get("n_exits") or 0)
    min_investment = int(form_data.get("min_investment") or 0)
    max_investment = int(form_data.get("max_investment") or 0)
    location = form_data.get("location")
    selected_round_names = form_data.get("round")
    selected_industry_names = form_data.get("industry")

    if not all(
        first_name,
        last_name,
        firm_name,
        about,
        email,
        phone_number,
        n_investments,
        n_exits,
        min_investment,
        max_investment,
        location,
        selected_round_names,
        selected_industry_names,
    ):
        status = ...
        return redirect("/admin/investor/create", code=302)

    investor = Investor(
        first_name=first_name,
        last_name=last_name,
        firm_name=firm_name,
        about=about,
        website=website,
        linkedin=linkedin,
        twitter=twitter,
        email=email,
        phone_number=phone_number,
        n_investments=n_investments,
        n_exits=n_exits,
        min_investment=min_investment,
        max_investment=max_investment,
        location=location,
        rounds=[Round.get_by_name(name) for name in selected_round_names],
        industries=[Industry.get_by_name(name) for name in selected_industry_names],
    )
    db.session.add(investor)
    db.session.commit()

    return redirect("/admin/investors", code=302)


@admin.post("/investor/<int:id>/delete")
@admin_only
def delete_investor(id):
    investor = Investor.get_by_id(id)

    if not investor:
        return jsonify({"message": "Investor not found"}), 404

    db.session.delete(investor)
    db.session.commit()

    return redirect("/admin", code=302)


@admin.route("/investment-firms")
@admin_only
def admin_investment_firm_view():
    investment_firms = InvestmentFirm.get_all()

    return render_template("admin/investment_firms.html", investment_firms=investment_firms)


@admin.route("/investment-firm/<int:id>")
@admin_only
def update_investment_firm_view(id):
    investment_firm = InvestmentFirm.get_by_id(id)

    return render_template("admin/update_investment_firm.html", investment_firm=investment_firm)


@admin.post("/investment-firm/<int:id>")
@admin_only
def update_investment_firm(id):
    form_data = request.get_json()

    investment_firm = InvestmentFirm.get_by_id(id)

    if not investment_firm:
        return jsonify({"message": "Investment Firm not found"}), 404

    name = form_data.get("name", investment_firm.name)
    about = form_data.get("about", investment_firm.about)
    website = form_data.get("website", investment_firm.website)
    email = form_data.get("email", investment_firm.email)
    phone_number = form_data.get("phone_number", investment_firm.phone_number)
    n_investments = int(form_data.get("n_investments", investment_firm.n_investments) or 0)
    n_exits = int(form_data.get("n_exits", investment_firm.n_exits) or 0)
    n_employees = int(form_data.get("n_employees", investment_firm.n_employees) or 0)
    min_investment = int(form_data.get("min_investment", investment_firm.min_investment) or 0)
    max_investment = int(form_data.get("max_investment", investment_firm.max_investment) or 0)
    location = form_data.get("location", investment_firm.location)

    if not all(
        name,
        about,
        email,
        phone_number,
        n_investments,
        n_exits,
        n_employees,
        min_investment,
        max_investment,
        location,
    ):
        status = ...
        return redirect(f"/admin/investment-firm/{id}", code=302)

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


@admin.get("/search_users/<search_input>")
@admin_only
def search_user(search_input):
    users = db.session.execute(select(User).where(User.email.contains(search_input))).scalars().all()

    return jsonify(users=[user.email for user in users])


@admin.route("/claim-requests")
@admin_only
def admin_claim_request_view():
    claim_requests = ClaimRequest.get_all()

    return render_template("admin/claim_requests.html", claim_requests=claim_requests)


@admin.get("/claim-request/<int:id>")
@admin_only
def edit_claim_request_view(id):
    claim_request = ClaimRequest.get_by_id(id)

    if not claim_request:
        return jsonify({"message": "Claim request not found"}), 404

    investor = Investor.get_by_id(claim_request.investor_id)
    if not investor:
        return jsonify({"message": "Investor not found"}), 404

    form_data = request.get_json()
    status = form_data.get("status")

    if status not in ["approved", "rejected"]:
        return jsonify({"message": "Invalid status"}), 400
    elif status == "approved":
        claim_request.status = RequestStatus.APPROVED.name  # type: ignore
        claim_request.approved_at = datetime.now(UTC)
        claim_request.approved_by = current_user.user_info.username
        investor.user = claim_request.user
    elif status == "rejected":
        claim_request.status = RequestStatus.REJECTED.name  # type: ignore
        investor.user = None
    db.session.commit()

    return jsonify({"message": "Claim request updated"}), 200


@admin.get("/investment-firm/create")
@admin_only
def create_investment_firm_view():
    return render_template(
        "admin/create_investment_firm.html",
        rounds=Round.get_all(),
        industries=Round.get_all(),
    )


@admin.post("/investment-firm/create")
@admin_only
def create_investment_firm():
    form_data = request.get_json()

    name = form_data.get("name")
    about = form_data.get("about")
    website = form_data.get("website")
    email = form_data.get("email")
    phone_number = form_data.get("phone_number")
    n_investments = int(form_data.get("n_investments") or 0)
    n_exits = int(form_data.get("n_exits") or 0)
    n_employees = int(form_data.get("n_employees") or 0)
    min_investment = int(form_data.get("min_investment") or 0)
    max_investment = int(form_data.get("max_investment") or 0)
    location = form_data.get("location")

    if not all(
        name,
        about,
        email,
        phone_number,
        n_investments,
        n_exits,
        n_employees,
        min_investment,
        max_investment,
        location,
    ):
        status = ...
        return redirect("/admin/investor/create", code=302)

    investor = InvestmentFirm(
        name=name,
        about=about,
        website=website,
        email=email,
        phone_number=phone_number,
        n_investments=n_investments,
        n_exits=n_exits,
        n_employees=n_employees,
        min_investment=min_investment,
        max_investment=max_investment,
        location=location,
    )

    db.session.add(investor)
    db.session.commit()

    return redirect("/admin/investment-firms", code=302)
