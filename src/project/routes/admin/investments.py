from datetime import datetime

from flask import Blueprint, redirect, render_template, request, url_for

from ...extensions import db
from ...models import (
    FundingRound,
    Investment,
    InvestmentFirm,
    Investor,
)
from ...schemas.investment import InvestmentSchema
from ...utils.decorators import admin_only
from ...utils.enums import (
    Status,
    StatusType,
)
from ...utils.funcs import generate_pagination

investment = Blueprint("investment", __name__)


@investment.get("/")
@admin_only
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    base_query = db.select(Investment).where(Investment.created_by_admin.is_(True))

    page = request.args.get("page", 1, type=int)

    pagination = db.paginate(base_query, page=page, per_page=9, error_out=False)

    investments = []

    for investment in pagination.items:
        if investment.investor:
            name = f"{investment.investor.first_name} {investment.investor.last_name}"
        elif investment.investment_firm:
            name = investment.investment_firm.name

        investments.append(
            InvestmentSchema(
                id=investment.id,
                name=name,
                amount=investment.amount,
                announced_date=investment.funding_round.announced_date.strftime("%b %d, %Y")
                if investment.funding_round.announced_date
                else None,
                round=investment.funding_round.round.name,
            )
        )

    total_pages = pagination.pages or 1

    pagination_info = generate_pagination(page, total_pages)

    return render_template(
        "admin/investments.html",
        investments=investments,
        status_type=status_type,
        msg=msg,
        pagination=pagination_info,
    )


@investment.get("/by-users")
@admin_only
def investments_by_users():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    base_query = db.select(Investment).where(Investment.created_by_admin.is_(False))

    page = request.args.get("page", 1, type=int)

    pagination = db.paginate(base_query, page=page, per_page=9, error_out=False)

    investments = []

    for investment in pagination.items:
        if investment.investor:
            name = f"{investment.investor.first_name} {investment.investor.last_name}"
        elif investment.investment_firm:
            name = investment.investment_firm.name

        investments.append(
            InvestmentSchema(
                id=investment.id,
                name=name,
                amount=investment.amount,
                announced_date=investment.funding_round.announced_date.strftime("%b %d, %Y")
                if investment.funding_round.announced_date
                else None,
                round=investment.funding_round.round.name,
            )
        )

    total_pages = pagination.pages or 1

    pagination_info = generate_pagination(page, total_pages)

    return render_template(
        "admin/investments_by_users.html",
        investments=investments,
        status_type=status_type,
        msg=msg,
        pagination=pagination_info,
    )


@investment.get("/create")
@admin_only
def create_investment_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template(
        "admin/create_investment.html",
        investors=Investor.get_all(),
        funding_rounds=FundingRound.get_all(),
        investment_firms=InvestmentFirm.get_all(),
        status_type=status_type,
        msg=msg,
    )


@investment.post("/create")
@admin_only
def create_investment():
    form_data = request.get_json()

    investment = Investment(
        investor_id=form_data.get("investor_id") or None,
        investment_firm_id=form_data.get("investment_firm_id") or None,
        description=form_data.get("description") or None,
        custom_name=form_data.get("custom_name") or None,
        amount=form_data.get("amount") or None,
        date=datetime.strptime(form_data.get("date"), "%Y-%m-%d"),
        funding_round_id=form_data.get("funding_round_id") or None,
        created_by_admin=True,
        is_verified=True,
    )

    try:
        db.session.add(investment)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment.create_investment_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investment created successfully!").get_status()
    return redirect(url_for("admin.investment.index", _external=True, **status))


@investment.get("/<int:id>")
@admin_only
def update_investment_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investment = Investment.get_by_id(id)
    if not investment:
        status = Status(StatusType.ERROR, "investment not found!").get_status()
        return redirect(url_for("admin.investment.index", _external=True, **status))

    return render_template(
        "admin/update_investment.html",
        investors=Investor.get_all(),
        investment=investment,
        funding_rounds=FundingRound.get_all(),
        status_type=status_type,
        investment_firms=InvestmentFirm.get_all(),
        msg=msg,
    )


@investment.post("/<int:id>")
@admin_only
def update_funding_round(id):
    form_data = request.get_json()

    investmet = Investment.get_by_id(id)
    if not investmet:
        status = Status(StatusType.ERROR, "Investment not found!").get_status()
        return redirect(url_for("admin.investment.index", _external=True, **status))

    investmet.investor_id = form_data.get("investor_id" or None)
    investmet.investment_firm_id = form_data.get("investment_firm_id") or None
    investmet.custom_name = form_data.get("custom_name") or None
    investmet.amount = form_data.get("amount") or None
    investmet.funding_round_id = form_data.get("funding_round_id") or None
    investmet.created_by_admin = form_data.get("created_by_admin")
    investmet.is_verified = form_data.get("is_verified")

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment.update_investment_view", id=id, _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investment updated successfully!").get_status()
    return redirect(url_for("admin.investment.update_investment_view", id=id, _external=True, **status))
