from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import or_, select

from ...extensions import db
from ...models import (
    EntityNotable,
    Industry,
    NotableInvestment,
    Person,
    Round,
    User,
    entity_search,
)
from ...models.entity import load_profile_bundle
from ...utils.decorators import admin_only
from ...utils.enums import (
    EntityType,
    Status,
    StatusType,
)
from ...utils.errors.error_messages import (
    EMPTY_FIRSTNAME,
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
    page = request.args.get("page", 1, type=int)
    try:
        result = entity_search.get_search(
            query=search_string or "*",
            entity_type="person",
            page=page,
            per_page=9,
        )
    except Exception:
        result = {"found": 0, "page": page, "hits": []}

    found = result.get("found", 0)
    pages = found // 9 + (1 if found % 9 else 0)
    investors = [hit.get("document", {}) for hit in result.get("hits", [])]
    pagination = generate_pagination(int(result.get("page", page)), max(pages, 1))

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
    page = request.args.get("page", 1, type=int)
    try:
        result = entity_search.get_search(
            query=search_string or "*",
            entity_type="person",
            page=page,
            per_page=9,
        )
    except Exception:
        result = {"found": 0, "page": page, "hits": []}

    found = result.get("found", 0)
    pages = found // 9 + (1 if found % 9 else 0)
    investors = [hit.get("document", {}) for hit in result.get("hits", [])]
    pagination = generate_pagination(int(result.get("page", page)), max(pages, 1))

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
    person = Person.get_by_id(id)
    if not person:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.approve_investors", _external=True, **status))

    person.is_public = True

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.approve_investors", _external=True, **status))

    try:
        entity_search.sync_one(EntityType.PERSON, person.id)
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

    person = Person.get_by_id(id)
    if not person:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    bundle = load_profile_bundle(EntityType.PERSON, person.id)

    return render_template(
        "admin/update_investor.html",
        investor=person,
        investments_by_round={},
        rounds=Round.get_all(),
        all_industries=Industry.get_all(),
        investor_industries=bundle["industries"],
        stages=bundle["stages"],
        profile=bundle["profile"],
        affiliations=bundle["affiliations"],
        geographies=bundle["geographies"],
        status_type=status_type,
        msg=msg,
    )


@investor.post("/<int:id>")
@admin_only
def update_investor(id):
    form_data = request.get_json()

    person = Person.get_by_id(id)
    if not person:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    first_name = form_data.get("first_name", person.first_name).strip()
    if not first_name:
        status = Status(StatusType.ERROR, EMPTY_FIRSTNAME).get_status()
        return redirect(url_for("admin.investor.update_investor_view", id=id, _external=True, **status))

    last_name = (form_data.get("last_name", person.last_name) or "").strip() or None

    # Optionally link to a user by email
    user_email = form_data.get("user_email")
    if user_email:
        user = User.get_by_email(user_email)
        if user:
            person.user_id = user.id
    elif "user_email" in form_data:
        person.user_id = None

    slug = form_data.get("slug", person.slug) or None
    old_slug = person.slug

    if slug and slug != person.slug:
        person.slug = slug

    if first_name != person.first_name or last_name != person.last_name:
        person.first_name = first_name
        person.last_name = last_name
        if not slug or slug == old_slug:
            person.set_slug()
    elif not slug:
        person.set_slug()

    if website := form_data.get("website", person.website):
        person.website = add_https_prefix(website)
    else:
        person.website = None

    if linkedin := form_data.get("linkedin", person.linkedin):
        person.linkedin = add_https_prefix(linkedin)
    else:
        person.linkedin = None

    if twitter := form_data.get("twitter", person.twitter):
        person.twitter = add_https_prefix(twitter)
    else:
        person.twitter = None

    person.about = form_data.get("about", person.about) or None
    person.email = form_data.get("email", person.email) or None
    person.phone_number = form_data.get("phone_number", person.phone_number) or None
    person.headline = form_data.get("headline", person.headline) or None
    person.is_public = form_data.get("is_public", person.is_public)
    person.is_approved = form_data.get("is_approved", person.is_approved)

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.update_investor_view", id=id, _external=True, **status))

    try:
        entity_search.sync_one(EntityType.PERSON, person.id)
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.update_investor_view", id=id, _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor updated successfully!").get_status()
    return redirect(url_for("admin.investor.update_investor_view", id=id, _external=True, **status))


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
    user_id = None
    if user_email:
        user = User.get_by_email(user_email)
        if user:
            user_id = user.id

    twitter = form_data.get("twitter") or None
    if isinstance(twitter, str) and "x.com" in twitter:
        slug_part = twitter.split("/")[-1]
        twitter = f"https://twitter.com/{slug_part}"

    slug = form_data.get("slug") or ""
    person = Person(
        first_name=first_name,
        last_name=form_data.get("last_name") or None,
        slug=slug,
        about=form_data.get("about") or None,
        headline=form_data.get("headline") or None,
        website=form_data.get("website") or None,
        linkedin=form_data.get("linkedin") or None,
        twitter=twitter,
        email=form_data.get("email") or None,
        phone_number=form_data.get("phone_number") or None,
        user_id=user_id,
    )

    try:
        db.session.add(person)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.create_investor_view", _external=True, **status))

    if not person.slug:
        person.set_slug()

    try:
        entity_search.sync_one(EntityType.PERSON, person.id)
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.create_investor_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor created successfully!").get_status()
    return redirect(url_for("admin.investor.index", _external=True, **status))


@investor.post("/<int:id>/delete")
@admin_only
def delete_investor(id):
    person = Person.get_by_id(id)
    if not person:
        status = Status(StatusType.ERROR, INVESTOR_NOT_FOUND).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    try:
        entity_search.delete_data(EntityType.PERSON, person.id)
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    try:
        db.session.delete(person)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.index", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor deleted successfully!").get_status()
    return redirect(url_for("admin.investor.index", _external=True, **status))


@investor.get("/search_notable_investments/<search_input>/<int:investor_id>")
@admin_only
def search_notable_investments(search_input, investor_id):
    person = Person.get_by_id(investor_id)
    if not person:
        return {"notable_investments": []}

    excluded_notable_investment_ids = db.session.scalars(
        db.select(EntityNotable.notable_investment_id).where(
            EntityNotable.entity_type == EntityType.PERSON,
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


@investor.get("/filter")
@admin_only
def filter_investors():
    query_params = request.args
    page = query_params.get("page", 1, type=int)
    per_page = query_params.get("per_page", 12, type=int)

    active_filters = {
        key: value
        for key, value in {
            "check_twitter": query_params.get("check_twitter") == "true",
            "check_linkedin": query_params.get("check_linkedin") == "true",
            "check_website": query_params.get("check_website") == "true",
            "check_about": query_params.get("check_about") == "true",
            "check_email": query_params.get("check_email") == "true",
        }.items()
        if value is True
    }

    base_query = db.select(Person)
    conditions = []

    if "check_about" in active_filters:
        conditions.append((Person.about.is_(None)) | (Person.about == ""))

    if "check_email" in active_filters:
        conditions.append((Person.email.is_(None)) | (Person.email == ""))

    if "check_twitter" in active_filters:
        conditions.append((Person.twitter.is_(None)) | (Person.twitter == ""))

    if "check_linkedin" in active_filters:
        conditions.append((Person.linkedin.is_(None)) | (Person.linkedin == ""))

    if "check_website" in active_filters:
        conditions.append((Person.website.is_(None)) | (Person.website == ""))

    if conditions:
        base_query = base_query.where(or_(*conditions))

    pagination = db.paginate(base_query, page=page, per_page=per_page, error_out=False)

    investors_data = []
    for person in pagination.items:
        investors_data.append(
            {
                "id": person.id,
                "name": person.full_name,
                "about": person.about,
                "email": person.email,
                "twitter": person.twitter,
                "linkedin": person.linkedin,
                "website": person.website,
            }
        )

    total_pages = pagination.pages or 1
    pagination_info = generate_pagination(page, total_pages, per_page)

    return render_template(
        "admin/filter_investors.html",
        investors=investors_data,
        total=pagination.total,
        pagination=pagination_info,
        total_pages=total_pages,
    )


@investor.get("/funding-rounds")
@admin_only
def get_funding_rounds():
    return {"funding_rounds": []}
