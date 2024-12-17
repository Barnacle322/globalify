from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import select

from ...extensions import db
from ...models import (
    Industry,
    Investor,
    InvestorBackup,
    InvestorOriginPoint,
    NotableInvestment,
    Round,
    User,
)
from ...utils.decorators import admin_only
from ...utils.enums import (
    Status,
    StatusType,
)
from ...utils.errors.error_messages import (
    EMPTY_FIRSTNAME,
    EMPTY_LASTNAME,
    INVESTOR_BACKUP_NOT_FOUND,
    INVESTOR_NOT_FOUND,
)
from ...utils.funcs import generate_pagination
from ...utils.scraper import add_https_prefix

investor = Blueprint("investor", __name__)


@investor.get("/")
@admin_only
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    search_string = request.args.get("search", "")
    result = Investor.get_search(
        query_string=search_string,
        query_by=[
            "location",
            "country",
            "rounds",
            "industries",
            "notable_investments",
            "name",
            "firm_name",
            "position",
        ],
        page=request.args.get("page", 1, type=int),
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
        status_type=status_type,
        msg=msg,
    )


@investor.get("/approve")
@admin_only
def approve_investors():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    search_string = request.args.get("search", "")
    result = Investor.get_search(
        query_string=search_string,
        query_by=[
            "location",
            "country",
            "rounds",
            "industries",
            "notable_investments",
            "name",
            "firm_name",
            "position",
        ],
        page=request.args.get("page", 1, type=int),
        per_page=9,
        is_approved=False,
    )

    investors = result.get("investors")
    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    return render_template(
        "admin/approve_investors.html",
        investors=investors,
        query=search_string,
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        status_type=status_type,
        msg=msg,
    )


@investor.post("/<int:id>/approve")
@admin_only
def approve_investor(id):
    investor = Investor.get_by_id(id)
    if not investor:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.approve_investors", _external=True, **status))

    investor.is_approved = True

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.approve_investors", _external=True, **status))

    try:
        investor.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.approve_investors", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor approved successfully!").get_status()
    return redirect(url_for("admin.investor.approve_investors", _external=True, **status))


@investor.get("/<int:id>")
@admin_only
def update_investor_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investor = Investor.get_by_id_with_investments(id)
    if not investor:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    return render_template(
        "admin/update_investor.html",
        investor=investor,
        rounds=Round.get_all(),
        industries=Industry.get_all(),
        status_type=status_type,
        msg=msg,
    )


@investor.post("/<int:id>")
@admin_only
def update_investor(id):
    form_data = request.get_json()

    investor = Investor.get_by_id(id)
    if not investor:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    first_name = form_data.get("first_name", investor.first_name).strip()
    if not first_name:
        status = Status(StatusType.ERROR, EMPTY_FIRSTNAME).get_status()
        return redirect(url_for("admin.investor.create_investor_view", _external=True, **status))

    last_name = form_data.get("last_name", investor.last_name).strip()
    if not last_name:
        status = Status(StatusType.ERROR, EMPTY_LASTNAME).get_status()
        return redirect(url_for("admin.investor.create_investor_view", _external=True, **status))

    investor_backup = InvestorBackup.get_by_investor_id(investor.id)
    if not investor_backup:
        investor_backup = InvestorBackup(investor=investor)
    investor_backup.first_name = investor.first_name
    investor_backup.last_name = investor.last_name
    investor_backup.slug = investor.slug
    investor_backup.firm_name = investor.firm_name
    investor_backup.about = investor.about
    investor_backup.position = investor.position
    investor_backup.website = investor.website
    investor_backup.linkedin = investor.linkedin
    investor_backup.twitter = investor.twitter
    investor_backup.email = investor.email
    investor_backup.phone_number = investor.phone_number
    investor_backup.n_investments = investor.n_investments
    investor_backup.n_exits = investor.n_exits
    investor_backup.min_investment = investor.min_investment
    investor_backup.max_investment = investor.max_investment
    investor_backup.location = investor.location
    investor_backup.notable_investments = investor.notable_investments
    investor_backup.rounds = investor.rounds
    investor_backup.industries = investor.industries
    investor_backup.user = investor.user

    db.session.add(investor_backup)

    # Claim investor profile to specific user and initiate point origin
    # if we delete user, point origin will be deleted as well
    user = User.get_by_email(form_data.get("user_email"))
    if user:
        investor.user = user
        investor_point_origin = InvestorOriginPoint.get_by_investor_id(investor.id)
        if not investor_point_origin:
            investor_point_origin = InvestorOriginPoint(investor_id=investor.id)
            investor_point_origin.first_name = investor.first_name
            investor_point_origin.last_name = investor.last_name
            investor_point_origin.slug = investor.slug
            investor_point_origin.firm_name = investor.firm_name
            investor_point_origin.about = investor.about
            investor_point_origin.position = investor.position
            investor_point_origin.website = investor.website
            investor_point_origin.linkedin = investor.linkedin
            investor_point_origin.twitter = investor.twitter
            investor_point_origin.email = investor.email
            investor_point_origin.phone_number = investor.phone_number
            investor_point_origin.n_investments = investor.n_investments
            investor_point_origin.n_exits = investor.n_exits
            investor_point_origin.min_investment = investor.min_investment
            investor_point_origin.max_investment = investor.max_investment
            investor_point_origin.location = investor.location
            investor_point_origin.notable_investments = investor.notable_investments
            investor_point_origin.rounds = investor.rounds
            investor_point_origin.industries = investor.industries
            db.session.add(investor_point_origin)
    else:
        investor.user = None
        investor_point_origin = InvestorOriginPoint.get_by_investor_id(investor.id)
        if investor_point_origin:
            db.session.delete(investor_point_origin)

    slug = form_data.get("slug", investor.slug) or None
    old_slug = investor.slug

    if slug and slug != investor.slug:
        investor.slug = slug

    if first_name != investor.first_name or last_name != investor.last_name:
        investor.first_name = first_name
        investor.last_name = last_name
        if not slug or slug == old_slug:
            investor.set_slug()
    elif not slug:
        investor.set_slug()

    if website := form_data.get("website", investor.website):
        investor.website = add_https_prefix(website)
    else:
        investor.website = None

    if linkedin := form_data.get("linkedin", investor.linkedin):
        investor.linkedin = add_https_prefix(linkedin)
    else:
        investor.linkedin = None

    if twitter := form_data.get("twitter", investor.twitter):
        investor.twitter = add_https_prefix(twitter)
    else:
        investor.twitter = None

    investor.firm_name = form_data.get("firm_name", investor.firm_name) or None
    investor.position = form_data.get("position", investor.position) or None
    investor.about = form_data.get("about", investor.about) or None
    investor.email = form_data.get("email", investor.email) or None
    investor.phone_number = form_data.get("phone_number", investor.phone_number) or None
    investor.location = form_data.get("location", investor.location) or None

    investor.n_investments = int(form_data.get("n_investments", investor.n_investments) or 0)
    investor.n_exits = int(form_data.get("n_exits", investor.n_exits) or 0)
    investor.min_investment = int(form_data.get("min_investment", investor.min_investment) or 0)
    investor.max_investment = int(form_data.get("max_investment", investor.max_investment) or 0)
    investor.location = form_data.get("location", investor.location) or None

    investor.rounds = list(Round.get_by_id_list(form_data.get("rounds", investor.rounds) or []))
    investor.industries = list(Industry.get_by_id_list(form_data.get("industries", investor.industries) or []))
    investor.notable_investments = list(
        NotableInvestment.get_by_id_list(form_data.get("notable_investments", investor.notable_investments) or [])
    )
    investor.is_public = form_data.get("is_public", investor.is_public)
    investor.is_approved = form_data.get("is_approved", investor.is_approved)

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.update_investor_view", id=id, _external=True, **status))

    try:
        investor.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.update_investor_view", id=id, _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor updated successfully!").get_status()
    return redirect(url_for("admin.investor.update_investor_view", id=id, _external=True, **status))


@investor.post("/<int:id>/undo")
@admin_only
def undo_investor_data(id):
    investor = Investor.get_by_id(id)
    if not investor:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    investor_backup = InvestorBackup.get_by_investor_id(investor.id)
    if not investor_backup:
        status = Status(StatusType.ERROR, INVESTOR_BACKUP_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    investor.first_name = investor_backup.first_name
    investor.last_name = investor_backup.last_name
    investor.slug = investor_backup.slug
    investor.firm_name = investor_backup.firm_name
    investor.position = investor_backup.position
    investor.about = investor_backup.about
    investor.website = investor_backup.website
    investor.linkedin = investor_backup.linkedin
    investor.twitter = investor_backup.twitter
    investor.email = investor_backup.email
    investor.phone_number = investor_backup.phone_number
    investor.n_investments = investor_backup.n_investments
    investor.n_exits = investor_backup.n_exits
    investor.min_investment = investor_backup.min_investment
    investor.max_investment = investor_backup.max_investment
    investor.location = investor_backup.location
    investor.rounds = investor_backup.rounds
    investor.industries = investor_backup.industries
    investor.notable_investments = investor_backup.notable_investments
    investor.user = investor_backup.user

    db.session.commit()
    investor.upsert_data()

    status = Status(StatusType.SUCCESS, "Investor backed up successfully!").get_status()
    return redirect(url_for("admin.investor.update_investor_view", id=id, _external=True, **status))


@investor.get("/<int:id>/restore")
@admin_only
def restore_investor_data(id):
    investor = Investor.get_by_id(id)
    if not investor:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    investor_point_origin = InvestorOriginPoint.get_by_investor_id(id)
    if investor_point_origin:
        investor.first_name = investor_point_origin.first_name
        investor.last_name = investor_point_origin.last_name
        investor.slug = investor_point_origin.slug
        investor.firm_name = investor_point_origin.firm_name
        investor.position = investor_point_origin.position
        investor.about = investor_point_origin.about
        investor.website = investor_point_origin.website
        investor.linkedin = investor_point_origin.linkedin
        investor.twitter = investor_point_origin.twitter
        investor.email = investor_point_origin.email
        investor.phone_number = investor_point_origin.phone_number
        investor.n_investments = investor_point_origin.n_investments
        investor.n_exits = investor_point_origin.n_exits
        investor.min_investment = investor_point_origin.min_investment
        investor.max_investment = investor_point_origin.max_investment
        investor.location = investor_point_origin.location
        investor.rounds = investor_point_origin.rounds
        investor.industries = investor_point_origin.industries
        investor.notable_investments = investor_point_origin.notable_investments

        db.session.commit()
        investor.upsert_data()
    else:
        status = Status(StatusType.ERROR, INVESTOR_BACKUP_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.index", id=id, _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor data restored.").get_status()
    return redirect(url_for("admin.investor.update_investor_view", id=id, _external=False, **status))


@investor.get("/create")
@admin_only
def create_investor_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template(
        "admin/create_investor.html",
        rounds=Round.get_all(),
        industries=Industry.get_all(),
        notable_investments=NotableInvestment.get_all(),
        status_type=status_type,
        msg=msg,
    )


@investor.post("/create")
@admin_only
def create_investor():
    form_data = request.get_json()

    first_name = form_data.get("first_name")
    if not first_name:
        status = Status(StatusType.ERROR, EMPTY_FIRSTNAME).get_status()
        return redirect(url_for("admin.investor.create_investor_view", _external=True, **status))

    user_email = form_data.get("user_email") or None
    if user_email:
        user = User.get_by_email(user_email)
    else:
        user = None

    investor = Investor(
        first_name=first_name,
        last_name=form_data.get("last_name"),
        slug=form_data.get("slug") or None,
        firm_name=form_data.get("firm_name") or None,
        position=form_data.get("position") or None,
        about=form_data.get("about") or None,
        website=form_data.get("website") or None,
        linkedin=form_data.get("linkedin") or None,
        twitter=form_data.get("twitter") or None,
        email=form_data.get("email") or None,
        phone_number=form_data.get("phone_number") or None,
        n_investments=int(form_data.get("n_investments") or 0),
        n_exits=int(form_data.get("n_exits") or 0),
        min_investment=int(form_data.get("min_investment") or 0),
        max_investment=int(form_data.get("max_investment") or 0),
        location=form_data.get("location") or None,
        rounds=list(Round.get_by_id_list(form_data.get("rounds") or [])),
        industries=list(Industry.get_by_id_list(form_data.get("industries") or [])),
        notable_investments=list(NotableInvestment.get_by_id_list(form_data.get("notable_investments") or [])),
        user=user,
    )

    try:
        db.session.add(investor)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.create_investor_view", _external=True, **status))

    if not investor.slug:
        investor.set_slug()

    try:
        investor.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.create_investor_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor created successfully!").get_status()
    return redirect(url_for("admin.investor.index", _external=True, **status))


@investor.post("/<int:id>/delete")
@admin_only
def delete_investor(id):
    investor = Investor.get_by_id(id)
    if not investor:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    try:
        investor.delete_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    try:
        db.session.delete(investor)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor deleted successfully!").get_status()
    return redirect(url_for("admin.investor.index", _external=True, **status))


@investor.get("/search_notable_investments/<search_input>/<int:investor_id>")
def search_notable_investments(search_input, investor_id):
    investor = Investor.get_by_id(investor_id)
    if not investor:
        return {"notable_investments": []}

    excluded_notable_investment_ids = [ni.id for ni in investor.notable_investments]

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


@investor.get("/filter")
@admin_only
def filter_investors():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    page = request.args.get("page", 1, type=int)

    stmt = db.select(Investor.id).where(Investor.slug.is_(None))

    batch_count = 1
    for investors in Investor.get_batches(batch_size=100, stmt=stmt):
        print(f"Processing batch {batch_count}")
        for investor in investors:
            print(investor)
        batch_count += 1

    pagination = db.paginate(stmt, page=page, per_page=9, error_out=False)

    total_pages = pagination.pages or 1
    pagination_info = generate_pagination(page, total_pages, 9)

    return render_template(
        "admin/filter_investors.html",
        investors=investors,
        pagination=pagination_info,
        total_pages=total_pages,
        status_type=status_type,
        msg=msg,
    )


@investor.get("/filter")
@admin_only
def filter_investors2():
    query_params = request.args
    page = query_params.get("page", 1, type=int)
    per_page = query_params.get("per_page", 12, type=int)

    filters = {
        "has_twitter": query_params.get("has_twitter", type=bool),
        "has_linkedin": query_params.get("has_linkedin", type=bool),
        "has_website": query_params.get("has_website", type=bool),
        "is_public": query_params.get("is_public", type=bool),
        "is_approved": query_params.get("is_approved", type=bool),
        "has_investments": query_params.get("has_investments", type=bool),
        "has_rounds": query_params.get("has_rounds", type=bool),
        "has_industries": query_params.get("has_industries", type=bool),
    }

    base_query = db.select(Investor)

    if filters.get("has_twitter") is True:
        base_query = base_query.where(Investor.twitter.is_not(None) & (Investor.twitter != ""))
    elif filters.get("has_twitter") is False:
        base_query = base_query.where((Investor.twitter.is_(None)) | (Investor.twitter == ""))

    if filters.get("has_linkedin") is True:
        base_query = base_query.where(Investor.linkedin.is_not(None) & (Investor.linkedin != ""))
    elif filters.get("has_linkedin") is False:
        base_query = base_query.where((Investor.linkedin.is_(None)) | (Investor.linkedin == ""))

    if filters.get("has_website") is True:
        base_query = base_query.where(Investor.website.is_not(None) & (Investor.website != ""))
    elif filters.get("has_website") is False:
        base_query = base_query.where((Investor.website.is_(None)) | (Investor.website == ""))

    if filters.get("is_public") is not None:
        base_query = base_query.where(Investor.is_public == filters["is_public"])

    if filters.get("is_approved") is not None:
        base_query = base_query.where(Investor.is_approved == filters["is_approved"])

    if filters.get("has_investments") is True:
        base_query = base_query.where(Investor.notable_investments.any())
    elif filters.get("has_investments") is False:
        base_query = base_query.where(~Investor.notable_investments.any())

    if filters.get("has_rounds") is True:
        base_query = base_query.where(Investor.rounds.any())
    elif filters.get("has_rounds") is False:
        base_query = base_query.where(~Investor.rounds.any())

    if filters.get("has_industries") is True:
        base_query = base_query.where(Investor.industries.any())
    elif filters.get("has_industries") is False:
        base_query = base_query.where(~Investor.industries.any())

    pagination = db.paginate(base_query, page=page, per_page=per_page, error_out=False)

    investors_data = []
    for investor in pagination.items:
        investors_data.append(
            {
                "id": investor.id,
                "name": investor.name,
                "twitter": investor.twitter,
                "linkedin": investor.linkedin,
                "website": investor.website,
                "is_public": investor.is_public,
                "is_approved": investor.is_approved,
                "n_investments": len(investor.notable_investments),
                "n_rounds": len(investor.rounds),
                "n_industries": len(investor.industries),
            }
        )

    total_pages = pagination.pages or 1
    pagination_info = generate_pagination(page, total_pages, per_page)

    return render_template(
        "admin/filter_investors.html",
        investors=investors_data,
        pagination=pagination_info,
        total_pages=total_pages,
        total_investors=pagination.total,
    )
