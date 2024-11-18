from datetime import datetime

from flask import Blueprint, redirect, render_template, request, url_for

from ...extensions import db
from ...models import (
    FundingRound,
    Round,
)
from ...schemas.funding_round import FundingRoundSchema
from ...utils.decorators import admin_only
from ...utils.enums import (
    Status,
    StatusType,
)
from ...utils.errors.error_messages import (
    EMPTY_ANNOUNCED_DATE,
    EMPTY_ORGANIZATION_NAME,
    EMPTY_ROUND_ID,
)
from ..main import generate_pagination

funding_round = Blueprint("funding_round", __name__)


@funding_round.get("/")
@admin_only
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    base_query = db.select(FundingRound).order_by(FundingRound.announced_date.desc())

    page = request.args.get("page", 1, type=int)

    pagination = db.paginate(base_query, page=page, per_page=9, error_out=False)

    funding_rounds = []

    for funding_round in pagination.items:
        funding_rounds.append(
            FundingRoundSchema(
                id=funding_round.id,
                organization_name=funding_round.organization_name,
                announced_date=funding_round.announced_date,
                round={
                    "id": funding_round.round.id,
                    "name": funding_round.round.name,
                },
            )
        )

    total_pages = pagination.pages or 1

    pagination_info = generate_pagination(page, total_pages)

    return render_template(
        "admin/funding_rounds.html",
        funding_rounds=funding_rounds,
        status_type=status_type,
        msg=msg,
        pagination=pagination_info,
    )


@funding_round.get("/create")
@admin_only
def create_funding_round_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template(
        "admin/create_funding_round.html",
        rounds=Round.get_all(),
        status_type=status_type,
        msg=msg,
    )


@funding_round.post("/create")
@admin_only
def create_funding_round():
    form_data = request.get_json()

    organization_name = form_data.get("organization_name")
    if not organization_name:
        status = Status(StatusType.ERROR, EMPTY_ORGANIZATION_NAME).get_status()
        return redirect(url_for("admin.funding_round.create_funding_round_view", _external=True, **status))

    announced_date = form_data.get("announced_date")
    if not announced_date:
        status = Status(StatusType.ERROR, EMPTY_ANNOUNCED_DATE).get_status()
        return redirect(url_for("admin.funding_round.create_funding_round_view", _external=True, **status))

    round_id = form_data.get("round_id")
    if not round_id:
        status = Status(StatusType.ERROR, EMPTY_ROUND_ID).get_status()
        return redirect(url_for("admin.funding_round.create_funding_round_view", _external=True, **status))

    announced_date_format = datetime.strptime(announced_date, "%Y-%m-%d")

    funding_round = FundingRound(
        organization_name=organization_name,
        announced_date=announced_date_format,
        round_id=round_id,
    )

    try:
        db.session.add(funding_round)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.funding_round.create_funding_round_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Funding round created successfully!").get_status()
    return redirect(url_for("admin.funding_round.index", _external=True, **status))
