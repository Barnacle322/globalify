from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import select

from ...extensions import db
from ...models import (
    Industry,
    InvestmentFirm,
    NotableInvestment,
    Round,
)
from ...routes.main import generate_pagination
from ...utils.decorators import admin_only
from ...utils.enums import (
    Status,
    StatusType,
)

investment_firm = Blueprint("investment_firm", __name__)


@investment_firm.get("")
@admin_only
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

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
        status_type=status_type,
        msg=msg,
    )


@investment_firm.get("/<int:id>")
@admin_only
def update_investment_firm_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investment_firm = InvestmentFirm.get_by_id_with_investments(id)
    if not investment_firm:
        status = Status(StatusType.ERROR, "Investment Firm not found").get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/update_investment_firm.html",
        investment_firm=investment_firm,
        rounds=rounds,
        industries=industries,
        status_type=status_type,
        msg=msg,
    )


@investment_firm.post("/<int:id>")
@admin_only
def update_investment_firm(id):
    form_data = request.get_json()

    investment_firm = InvestmentFirm.get_by_id(id)

    if not investment_firm:
        status = Status(StatusType.ERROR, "Investment Firm not found").get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    name = form_data.get("name", investment_firm.name)
    slug = form_data.get("slug", investment_firm.slug) or None

    about = form_data.get("about", investment_firm.about) or None
    location = form_data.get("location", investment_firm.location) or None

    selected_round_ids = form_data.get("rounds", investment_firm.rounds) or []
    selected_industry_ids = form_data.get("industries", investment_firm.industries) or []
    selected_notable_investment_ids = form_data.get("notable_investments", investment_firm.notable_investments) or []

    n_investments = int(form_data.get("n_investments", investment_firm.n_investments) or 0)
    n_exits = int(form_data.get("n_exits", investment_firm.n_exits) or 0)
    n_employees = int(form_data.get("n_employees", investment_firm.n_employees) or 0)
    min_investment = int(form_data.get("min_investment", investment_firm.min_investment) or 0)
    max_investment = int(form_data.get("max_investment", investment_firm.max_investment) or 0)

    website = form_data.get("website", investment_firm.website) or None
    email = form_data.get("email", investment_firm.email) or None
    phone_number = form_data.get("phone_number", investment_firm.phone_number) or None

    if not name:
        status = Status(StatusType.ERROR, "Name cannot be empty!").get_status()
        return redirect(url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=True, **status))

    if not slug:
        investment_firm.set_slug()
    else:
        investment_firm.slug = slug

    if email:
        existing_email = InvestmentFirm.get_by_email(email)
        if existing_email and existing_email.id != investment_firm.id:
            status = Status(StatusType.ERROR, "Email already exists").get_status()
            return redirect(
                url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=True, **status)
            )

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

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=True, **status))

    try:
        investment_firm.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investment Firm updated successfully!").get_status()
    return redirect(url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=True, **status))


@investment_firm.get("/create")
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


@investment_firm.post("/create")
@admin_only
def create_investment_firm():
    form_data = request.get_json()

    name = form_data.get("name")
    slug = form_data.get("slug") or None
    location = form_data.get("location") or None
    about = form_data.get("about") or None

    selected_round_ids = form_data.get("rounds") or []
    selected_industry_ids = form_data.get("industries") or []
    selected_notable_investment_names = form_data.get("notable_investments") or []

    n_investments = int(form_data.get("n_investments") or 0)
    n_exits = int(form_data.get("n_exits") or 0)
    n_employees = int(form_data.get("n_employees") or 0)
    min_investment = int(form_data.get("min_investment") or 0)
    max_investment = int(form_data.get("max_investment") or 0)

    website = form_data.get("website") or None
    email = form_data.get("email") or None
    phone_number = form_data.get("phone_number") or None

    if not name:
        status = Status(StatusType.ERROR, "Name cannot be empty!").get_status()
        return redirect(url_for("admin.investment_firm.create_investment_firm_view", _external=True, **status))

    if email:
        existing_email = InvestmentFirm.get_by_email(email)
        if existing_email:
            status = Status(StatusType.ERROR, "Email already exists").get_status()
            return redirect(url_for("admin.investment_firm.create_investment_firm_view", _external=True, **status))

    investment_firm = InvestmentFirm(
        name=name,
        slug=slug,
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
        rounds=list(Round.get_by_id_list(selected_round_ids)),
        industries=list(Industry.get_by_id_list(selected_industry_ids)),
        notable_investments=list(NotableInvestment.get_by_names(selected_notable_investment_names)),
    )

    try:
        db.session.add(investment_firm)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.create_investment_firm_view", _external=True, **status))

    if not investment_firm.slug:
        investment_firm.set_slug()

    try:
        investment_firm.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.create_investment_firm_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investment Firm created successfully!").get_status()
    return redirect(url_for("admin.investment_firm.index", _external=True, **status))


@investment_firm.post("/<int:id>/delete")
@admin_only
def delete_investment_firm(id):
    investment_firm = InvestmentFirm.get_by_id(id)

    if not investment_firm:
        status = Status(StatusType.ERROR, "Investment Firm not found").get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    try:
        investment_firm.delete_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    try:
        db.session.delete(investment_firm)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    return redirect("admin.investment_firm.index", code=302)


@investment_firm.get("/search_notable_investments/<search_input>/<int:investor_id>")
@admin_only
def search_notable_investments(search_input, investor_id):
    investment_firm = InvestmentFirm.get_by_id(investor_id)
    if not investment_firm:
        return {"notable_investments": []}

    excluded_notable_investment_ids = [ni.id for ni in investment_firm.notable_investments]

    notable_investments = (
        db.session.execute(
            select(NotableInvestment)
            .where(NotableInvestment.name.contains(search_input))
            .where(NotableInvestment.id.notin_(excluded_notable_investment_ids))
        )
        .scalars()
        .all()
    )

    return {"notable_investments": [ni.to_dict() for ni in notable_investments]}
