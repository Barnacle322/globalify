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
from ...utils.errors.error_messages import (
    EMAIL_ALREADY_USED,
    EMPTY_INVESTMENT_FIRM_NAME,
    INVESTMENT_FIRM_NOT_FOUND,
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
    result = InvestmentFirm.get_search(
        query_string=search_string,
        query_by=[
            "location",
            "country",
            "rounds",
            "industries",
            "embedding",
            "notable_investments",
            "name",
        ],
        page=request.args.get("page", 1, type=int),
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
        status = Status(StatusType.ERROR, INVESTMENT_FIRM_NOT_FOUND).get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    return render_template(
        "admin/update_investment_firm.html",
        investment_firm=investment_firm,
        rounds=Round.get_all(),
        industries=Industry.get_all(),
        status_type=status_type,
        msg=msg,
    )


@investment_firm.post("/<int:id>")
@admin_only
def update_investment_firm(id):
    form_data = request.get_json()

    investment_firm = InvestmentFirm.get_by_id(id)
    if not investment_firm:
        status = Status(StatusType.ERROR, INVESTMENT_FIRM_NOT_FOUND).get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    name = form_data.get("name", investment_firm.name)
    if not name:
        status = Status(StatusType.ERROR, EMPTY_INVESTMENT_FIRM_NAME).get_status()
        return redirect(url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=True, **status))

    slug = form_data.get("slug", investment_firm.slug) or None
    if not slug:
        investment_firm.set_slug()
    else:
        investment_firm.slug = slug

    email = form_data.get("email", investment_firm.email) or None
    if email:
        existing_email = InvestmentFirm.get_by_email(email)
        if existing_email and existing_email.id != investment_firm.id:
            status = Status(StatusType.ERROR, EMAIL_ALREADY_USED).get_status()
            return redirect(
                url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=True, **status)
            )

    investment_firm.name = name
    investment_firm.about = form_data.get("about", investment_firm.about) or None
    investment_firm.website = form_data.get("website", investment_firm.website) or None
    investment_firm.email = email
    investment_firm.phone_number = form_data.get("phone_number", investment_firm.phone_number) or None
    investment_firm.n_investments = int(form_data.get("n_investments", investment_firm.n_investments) or 0)
    investment_firm.n_exits = int(form_data.get("n_exits", investment_firm.n_exits) or 0)
    investment_firm.n_employees = int(form_data.get("n_employees", investment_firm.n_employees) or 0)
    investment_firm.min_investment = int(form_data.get("min_investment", investment_firm.min_investment) or 0)
    investment_firm.max_investment = int(form_data.get("max_investment", investment_firm.max_investment) or 0)
    investment_firm.location = form_data.get("location", investment_firm.location) or None
    investment_firm.rounds = list(Round.get_by_id_list(form_data.get("rounds", investment_firm.rounds) or []))
    investment_firm.industries = list(
        Industry.get_by_id_list(form_data.get("industries", investment_firm.industries) or [])
    )
    investment_firm.notable_investments = list(
        NotableInvestment.get_by_id_list(
            form_data.get("notable_investments", investment_firm.notable_investments) or []
        )
    )

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

    return render_template(
        "admin/create_investment_firm.html",
        rounds=Round.get_all(),
        industries=Industry.get_all(),
        notable_investments=NotableInvestment.get_all(),
        status_type=status_type,
        msg=msg,
    )


@investment_firm.post("/create")
@admin_only
def create_investment_firm():
    form_data = request.get_json()

    name = form_data.get("name")
    if not name:
        status = Status(StatusType.ERROR, EMPTY_INVESTMENT_FIRM_NAME).get_status()
        return redirect(url_for("admin.investment_firm.create_investment_firm_view", _external=True, **status))

    email = form_data.get("email") or None
    if email:
        existing_email = InvestmentFirm.get_by_email(email)
        if existing_email:
            status = Status(StatusType.ERROR, EMAIL_ALREADY_USED).get_status()
            return redirect(url_for("admin.investment_firm.create_investment_firm_view", _external=True, **status))

    investment_firm = InvestmentFirm(
        name=name,
        slug=form_data.get("slug") or None,
        about=form_data.get("about") or None,
        website=form_data.get("website") or None,
        email=email,
        phone_number=form_data.get("phone_number") or None,
        n_investments=int(form_data.get("n_investments") or 0),
        n_exits=int(form_data.get("n_exits") or 0),
        n_employees=int(form_data.get("n_employees") or 0),
        min_investment=int(form_data.get("min_investment") or 0),
        max_investment=int(form_data.get("max_investment") or 0),
        location=form_data.get("location") or None,
        rounds=list(Round.get_by_id_list(form_data.get("notable_investments") or [])),
        industries=list(Industry.get_by_id_list(form_data.get("industries") or [])),
        notable_investments=list(NotableInvestment.get_by_id_list(form_data.get("notable_investments") or [])),
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
        status = Status(StatusType.ERROR, INVESTMENT_FIRM_NOT_FOUND).get_status()
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
