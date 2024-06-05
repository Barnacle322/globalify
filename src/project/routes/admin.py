from datetime import UTC, datetime
from functools import wraps

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import (
    ClaimRequest,
    Industry,
    InvestmentFirm,
    Investor,
    NotableInvestment,
    Round,
    User,
)
from ..routes.main import generate_pagination
from ..utils.enums import (
    RequestStatus,
    Status,
    StatusType,
)
from ..utils.errors.error_messages import (
    AUTH_FIELDS_INCOMPLETE,
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


@admin.route("/investors")
@admin_only
def admin_investor_view():
    search_string = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)

    query_by = [
        "location",
        "country",
        "rounds",
        "industries",
        "notable_investments",
        "name",
        "firm_name",
        "position",
    ]

    result = Investor.get_search(
        query_string=search_string,
        query_by=query_by,
        page=page,
        per_page=9,
    )
    investors = result.get("investors")

    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    return render_template(
        "admin/investors.html",
        investors=investors,
        query=search_string,
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
    )


@admin.get("/investor/<int:id>")
@admin_only
def update_investor_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investor = Investor.get_by_id(id)

    notable_investments = NotableInvestment.get_all()
    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/update_investor.html",
        investor=investor,
        rounds=rounds,
        industries=industries,
        notable_investments=notable_investments,
        status_type=status_type,
        msg=msg,
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
    selected_notable_investment_ids = form_data.get("notable_investment", investor.notable_investments)

    website = form_data.get("website", investor.website)
    linkedin = form_data.get("linkedin", investor.linkedin)
    twitter = form_data.get("twitter", investor.twitter)
    email = form_data.get("email", investor.email)
    phone_number = form_data.get("phone_number", investor.phone_number)

    if not all(
        (
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
        )
    ):
        status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
        return redirect(url_for("admin.update_investor_view", id=id, _external=True, **status))

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
    investor.notable_investments = list(NotableInvestment.get_by_id_list(selected_notable_investment_ids))

    db.session.commit()

    return redirect("/admin/investors", code=302)


@admin.get("/investor/create")
@admin_only
def create_investor_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    notable_investments = NotableInvestment.get_all()
    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/create_investor.html",
        rounds=rounds,
        industries=industries,
        notable_investments=notable_investments,
        status_type=status_type,
        msg=msg,
    )


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
    selected_notable_investment_names = form_data.get("notable_investment")

    if not all(
        (
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
        )
    ):
        status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
        return redirect(url_for("admin.create_investor_view", _external=True, **status))

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
        notable_investments=[NotableInvestment.get_by_name(name) for name in selected_notable_investment_names],
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
    search_string = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)

    query_by = [
        "location",
        "country",
        "rounds",
        "industries",
        "embedding",
        "notable_investments",
        "name",
    ]

    result = InvestmentFirm.get_search(
        query_string=search_string,
        query_by=query_by,
        page=page,
        per_page=9,
    )
    investment_firms = result.get("investment_firms")

    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    return render_template(
        "admin/investment_firms.html",
        investment_firms=investment_firms,
        query=search_string,
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
    )


@admin.route("/investment-firm/<int:id>")
@admin_only
def update_investment_firm_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investment_firm = InvestmentFirm.get_by_id(id)

    notable_investments = NotableInvestment.get_all()
    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/update_investment_firm.html",
        investment_firm=investment_firm,
        rounds=rounds,
        industries=industries,
        notable_investments=notable_investments,
        status_type=status_type,
        msg=msg,
    )


@admin.post("/investment-firm/<int:id>")
@admin_only
def update_investment_firm(id):
    data = request.get_json()
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
    selected_round_ids = form_data.get("round", investment_firm.rounds)
    selected_industry_ids = form_data.get("industry", investment_firm.industries)
    selected_notable_investment_ids = form_data.get("notable_investment", investment_firm.notable_investments)

    if not all(
        (
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
        )
    ):
        status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
        return redirect(url_for("admin.update_investment_firm_view", id=id, _external=True, **status))

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
    investment_firm.rounds = list(Round.get_by_id_list(selected_round_ids))
    investment_firm.industries = list(Industry.get_by_id_list(selected_industry_ids))
    investment_firm.notable_investments = list(NotableInvestment.get_by_id_list(selected_notable_investment_ids))

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
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    notable_investments = NotableInvestment.get_all()
    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/create_investment_firm.html",
        rounds=rounds,
        industries=industries,
        notable_investments=notable_investments,
        status_type=status_type,
        msg=msg,
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
    selected_round_names = form_data.get("round")
    selected_industry_names = form_data.get("industry")
    selected_notable_investment_names = form_data.get("notable_investment")

    if not all(
        (
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
        )
    ):
        status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
        return redirect(url_for("admin.create_investment_firm_view", _external=True, **status))

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
        rounds=[Round.get_by_name(name) for name in selected_round_names],
        industries=[Industry.get_by_name(name) for name in selected_industry_names],
        notable_investments=[NotableInvestment.get_by_name(name) for name in selected_notable_investment_names],
    )

    db.session.add(investor)
    db.session.commit()

    return redirect("/admin/investment-firms", code=302)
