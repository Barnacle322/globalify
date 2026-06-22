from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import or_, select

from ...extensions import db
from ...models import (
    EntityNotable,
    Industry,
    NotableInvestment,
    Organization,
    Round,
    entity_search,
)
from ...utils.decorators import admin_only
from ...utils.enums import (
    EntityType,
    OrgType,
    Status,
    StatusType,
)
from ...utils.errors.error_messages import (
    EMAIL_ALREADY_USED,
    EMPTY_INVESTMENT_FIRM_NAME,
    INVESTMENT_FIRM_NOT_FOUND,
)
from ...utils.funcs import generate_pagination
from ...utils.scraper import add_https_prefix

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
    try:
        result = entity_search.get_search(
            query=search_string or "*",
            entity_type="org",
            page=page,
            per_page=9,
        )
    except Exception:
        result = {"found": 0, "page": page, "hits": []}

    found = result.get("found", 0)
    pages = found // 9 + (1 if found % 9 else 0)
    investment_firms = [hit.get("document", {}) for hit in result.get("hits", [])]
    pagination = generate_pagination(int(result.get("page", page)), max(pages, 1))

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

    org = Organization.get_by_id(id)
    if not org:
        status = Status(StatusType.ERROR, INVESTMENT_FIRM_NOT_FOUND).get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    return render_template(
        "admin/update_investment_firm.html",
        investment_firm=org,
        investments=[],
        rounds=Round.get_all(),
        industries=Industry.get_all(),
        status_type=status_type,
        msg=msg,
    )


@investment_firm.post("/<int:id>")
@admin_only
def update_investment_firm(id):
    form_data = request.get_json()

    org = Organization.get_by_id(id)
    if not org:
        status = Status(StatusType.ERROR, INVESTMENT_FIRM_NOT_FOUND).get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    investment_firm_name = form_data.get("name", org.name).strip()
    if not investment_firm_name:
        status = Status(StatusType.ERROR, EMPTY_INVESTMENT_FIRM_NAME).get_status()
        return redirect(url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=True, **status))

    email = form_data.get("email", org.email) or None
    if email:
        existing_email = Organization.get_by_email(email)
        if existing_email and existing_email.id != org.id:
            status = Status(StatusType.ERROR, EMAIL_ALREADY_USED).get_status()
            return redirect(
                url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=True, **status)
            )

    website_url = form_data.get("website", org.website) or None
    if website_url:
        website_url = add_https_prefix(website_url)
        try:
            org.website = website_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(
                url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=False, **status)
            )
    else:
        org.website = None

    slug = form_data.get("slug") or None
    if slug and slug != org.slug:
        org.slug = slug
    elif investment_firm_name != org.name:
        org.name = investment_firm_name
        org.set_slug()

    org.about = form_data.get("about", org.about) or None
    org.email = email
    org.phone_number = form_data.get("phone_number", org.phone_number) or None
    org.n_employees = int(form_data.get("n_employees", org.n_employees) or 0) or None
    org.is_public = form_data.get("is_public", org.is_public)

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.update_investment_firm_view", id=id, _external=True, **status))

    try:
        entity_search.sync_one(EntityType.ORG, org.id)
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
        existing_email = Organization.get_by_email(email)
        if existing_email:
            status = Status(StatusType.ERROR, EMAIL_ALREADY_USED).get_status()
            return redirect(url_for("admin.investment_firm.create_investment_firm_view", _external=True, **status))

    if website := form_data.get("website", ""):
        website = add_https_prefix(website)
    else:
        website = None

    slug = form_data.get("slug") or ""
    org = Organization(
        name=name,
        slug=slug,
        org_type=OrgType.VC_FIRM,
        about=form_data.get("about") or None,
        website=website,
        email=email,
        phone_number=form_data.get("phone_number") or None,
        n_employees=int(form_data.get("n_employees") or 0) or None,
    )

    try:
        db.session.add(org)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.create_investment_firm_view", _external=True, **status))

    if not org.slug:
        org.set_slug()

    try:
        entity_search.sync_one(EntityType.ORG, org.id)
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.create_investment_firm_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investment Firm created successfully!").get_status()
    return redirect(url_for("admin.investment_firm.index", _external=True, **status))


@investment_firm.post("/<int:id>/delete")
@admin_only
def delete_investment_firm(id):
    org = Organization.get_by_id(id)

    if not org:
        status = Status(StatusType.ERROR, INVESTMENT_FIRM_NOT_FOUND).get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    try:
        entity_search.delete_data(EntityType.ORG, org.id)
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    try:
        db.session.delete(org)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investment_firm.index", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investment Firm deleted successfully!").get_status()
    return redirect(url_for("admin.investment_firm.index", _external=True, **status))


@investment_firm.get("/search_notable_investments/<search_input>/<int:investor_id>")
@admin_only
def search_notable_investments(search_input, investor_id):
    org = Organization.get_by_id(investor_id)
    if not org:
        return {"notable_investments": []}

    excluded_notable_investment_ids = db.session.scalars(
        db.select(EntityNotable.notable_investment_id).where(
            EntityNotable.entity_type == EntityType.ORG,
            EntityNotable.entity_id == investor_id,
        )
    ).all()

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


@investment_firm.get("/filter")
@admin_only
def filter_investment_firms():
    query_params = request.args
    page = query_params.get("page", 1, type=int)
    per_page = query_params.get("per_page", 12, type=int)

    active_filters = {
        key: value
        for key, value in {
            "check_about": query_params.get("check_about") == "true",
            "check_email": query_params.get("check_email") == "true",
            "check_twitter": query_params.get("check_twitter") == "true",
            "check_linkedin": query_params.get("check_linkedin") == "true",
            "check_website": query_params.get("check_website") == "true",
        }.items()
        if value is True
    }

    base_query = db.select(Organization)
    conditions = []

    if "check_about" in active_filters:
        conditions.append((Organization.about.is_(None)) | (Organization.about == ""))

    if "check_email" in active_filters:
        conditions.append((Organization.email.is_(None)) | (Organization.email == ""))

    if "check_twitter" in active_filters:
        conditions.append((Organization.twitter.is_(None)) | (Organization.twitter == ""))

    if "check_linkedin" in active_filters:
        conditions.append((Organization.linkedin.is_(None)) | (Organization.linkedin == ""))

    if "check_website" in active_filters:
        conditions.append((Organization.website.is_(None)) | (Organization.website == ""))

    if conditions:
        base_query = base_query.where(or_(*conditions))

    pagination = db.paginate(base_query, page=page, per_page=per_page, error_out=False)

    investment_firms_data = []
    for org in pagination.items:
        investment_firms_data.append(
            {
                "id": org.id,
                "name": org.name,
                "about": org.about,
                "email": org.email,
                "twitter": org.twitter,
                "linkedin": org.linkedin,
                "website": org.website,
            }
        )

    total_pages = pagination.pages or 1
    pagination_info = generate_pagination(page, total_pages, per_page)

    return render_template(
        "admin/filter_investment_firms.html",
        investment_firms=investment_firms_data,
        total=pagination.total,
        pagination=pagination_info,
        total_pages=total_pages,
    )
