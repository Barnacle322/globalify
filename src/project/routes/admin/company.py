from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from sqlalchemy import select

from ...extensions import db
from ...models import (
    Company,
    Country,
    Industry,
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
    COMPANY_NOT_FOUND,
    EMPTY_COMPANY_NAME,
    PICTURE_NOT_LOADED,
)
from ...utils.google_helpers.google_storage import delete_blob_from_url, upload_picture
from ...utils.scraper import add_https_prefix

company = Blueprint("company", __name__)


@company.get("/search_notable_investments/<search_input>")
def search_notable_investment(search_input):
    notable_investments = (
        db.session.execute(
            select(NotableInvestment)
            .where(NotableInvestment.name.contains(search_input))
            .where(NotableInvestment.company_id.is_(None))
        )
        .scalars()
        .all()
    )

    return jsonify(
        notable_investments=[
            {"id": notable_investment.id, "name": notable_investment.name} for notable_investment in notable_investments
        ]
    )


@company.get("/")
@admin_only
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    search_string = request.args.get("search", "")
    result = Company.get_search(
        query_string=search_string,
        query_by=[
            "country",
            "preferred_round",
            "industry",
            "embedding",
            "name",
        ],
        page=request.args.get("page", 1, type=int),
        per_page=9,
    )
    companies = result.get("companies")
    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    return render_template(
        "admin/companies.html",
        companies=companies,
        query=search_string,
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        status_type=status_type,
        msg=msg,
    )


@company.get("/<int:id>")
@admin_only
def update_company_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    company = Company.get_by_id(id)
    if not company:
        status = Status(StatusType.ERROR, COMPANY_NOT_FOUND).get_status()
        return redirect(url_for("admin.company.index", _external=True, **status))

    return render_template(
        "admin/update_company.html",
        company=company,
        rounds=Round.get_all(),
        industries=Industry.get_all(),
        countries=Country.get_all(),
        status_type=status_type,
        msg=msg,
    )


@company.post("/<int:id>")
@admin_only
def update_company(id):
    form_data = request.get_json()

    print("\n\n\n\n\n\n\n\n\n\n")
    print(form_data)

    company = Company.get_by_id(id)
    if not company:
        status = Status(StatusType.ERROR, COMPANY_NOT_FOUND).get_status()
        return redirect(url_for("admin.company.index", _external=True, **status))

    name = form_data.get("name", company.name)
    if not name:
        status = Status(StatusType.ERROR, EMPTY_COMPANY_NAME).get_status()
        return redirect(url_for("admin.company.update_company_view", id=id, _external=True, **status))

    slug = form_data.get("slug", company.slug) or None
    if not slug:
        company.set_slug()
    else:
        company.slug = slug

    website_url = form_data.get("website", company.website_url) or None
    if website_url:
        website_url = add_https_prefix(website_url)
        try:
            company.website_url = website_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("admin.company.update_company_view", id=id, _external=False, **status))
    else:
        company.website_url = None

    linkedin_url = form_data.get("linkedin", company.linkedin_url) or None
    if linkedin_url:
        linkedin_url = add_https_prefix(linkedin_url)
        try:
            company.linkedin_url = linkedin_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("admin.company.update_company_view", id=id, _external=False, **status))
    else:
        company.linkedin_url = None

    instagram_url = form_data.get("instagram", company.instagram_url) or None
    if instagram_url:
        instagram_url = add_https_prefix(instagram_url)
        try:
            company.instagram_url = instagram_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("admin.company.update_company_view", id=id, _external=False, **status))
    else:
        company.instagram_url = None

    twitter_url = form_data.get("twitter", company.twitter_url) or None
    if twitter_url:
        twitter_url = add_https_prefix(twitter_url)
        try:
            company.twitter_url = twitter_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("admin.company.update_company_view", id=id, _external=False, **status))
    else:
        company.twitter_url = None

    picture = request.files.get("picture") or None
    if picture:
        try:
            picture_url = upload_picture(picture)
            if company.picture_url:
                try:
                    delete_blob_from_url(company.picture_url)
                except Exception as e:
                    print(e)
            company.picture_url = picture_url
        except Exception as e:
            print(e)
            status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
            return redirect(url_for("admin.company.update_company_view", _external=False, **status))

    company.name = name
    company.description = form_data.get("description", company.description) or None
    company.number_of_employees = int(form_data.get("number_of_employees", company.number_of_employees) or 0)
    company.website_url = website_url
    company.linkedin_url = linkedin_url
    company.instagram_url = instagram_url
    company.twitter_url = twitter_url
    company.country_id = form_data.get("country", company.country) or None
    company.preferred_round_id = form_data.get("preferred_round", company.preferred_round) or None
    company.industry_id = form_data.get("industry", company.industry) or None
    company.is_public = form_data.get("is_public", company.is_public) or False

    notable_investment_name = form_data.get("notable_investment") or None
    if notable_investment_name:
        notable_investment = NotableInvestment.get_by_name(notable_investment_name)
        if notable_investment:
            if notable_investment.company:
                status = Status(
                    StatusType.ERROR, "Notable investment already associated with another company"
                ).get_status()
                return redirect(url_for("admin.company.update_company_view", id=id, _external=True, **status))
            if notable_investment.company != company:
                notable_investment.company = company

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.company.update_company_view", id=id, _external=True, **status))

    try:
        company.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.company.update_company_view", id=id, _external=True, **status))

    status = Status(StatusType.SUCCESS, "Company updated successfully!").get_status()
    return redirect(url_for("admin.company.update_company_view", id=id, _external=True, **status))


@company.get("/create")
@admin_only
def create_company_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template(
        "admin/create_company.html",
        rounds=Round.get_all(),
        industries=Industry.get_all(),
        countries=Country.get_all(),
        status_type=status_type,
        msg=msg,
    )


@company.post("/create")
@admin_only
def create_company():
    form_data = request.get_json()

    name = form_data.get("name")
    if not name:
        status = Status(StatusType.ERROR, EMPTY_COMPANY_NAME).get_status()
        return redirect(url_for("admin.company.create_company_view", _external=True, **status))

    company = Company(name=name)

    slug = form_data.get("slug") or None
    if not slug:
        company.set_slug()
    else:
        company.slug = slug

    website_url = form_data.get("website") or None
    if website_url:
        website_url = add_https_prefix(website_url)
        try:
            company.website_url = website_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.company_info_view", id=id, _external=False, **status))
    else:
        company.website_url = None

    linkedin_url = form_data.get("linkedin") or None
    if linkedin_url:
        linkedin_url = add_https_prefix(linkedin_url)
        try:
            company.linkedin_url = linkedin_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.company_info_view", id=id, _external=False, **status))
    else:
        company.linkedin_url = None

    instagram_url = form_data.get("instagram") or None
    if instagram_url:
        instagram_url = add_https_prefix(instagram_url)
        try:
            company.instagram_url = instagram_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.company_info_view", id=id, _external=False, **status))
    else:
        company.instagram_url = None

    twitter_url = form_data.get("twitter") or None
    if twitter_url:
        twitter_url = add_https_prefix(twitter_url)
        try:
            company.twitter_url = twitter_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.company_info_view", id=id, _external=False, **status))
    else:
        company.twitter_url = None

    picture = request.files.get("picture") or None
    if picture:
        try:
            picture_url = upload_picture(picture)
            company.picture_url = picture_url
        except Exception as e:
            print(e)
            status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
            return redirect(url_for("settings.create_company_view", _external=False, **status))

    company.description = form_data.get("description") or None
    company.number_of_employees = int(form_data.get("number_of_employees") or 0)

    company.country_id = form_data.get("country") or None
    company.preferred_round_id = form_data.get("preferred_round") or None
    company.industry_id = form_data.get("industry") or None

    company.is_public = form_data.get("is_public") or False

    notable_investment_name = form_data.get("notable_investment")
    if notable_investment_name:
        notable_investment = NotableInvestment.get_by_name(notable_investment_name)
        if notable_investment:
            notable_investment.company = company

    try:
        db.session.add(company)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.company.create_company_view", _external=True, **status))

    if not company.slug:
        company.set_slug()

    try:
        company.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.company.create_company_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Company created successfully!").get_status()
    return redirect(url_for("admin.company.index", _external=True, **status))


@company.post("/<int:id>/delete")
@admin_only
def delete_company(id):
    company = Company.get_by_id(id)

    if not company:
        status = Status(StatusType.ERROR, COMPANY_NOT_FOUND).get_status()
        return redirect(url_for("admin.company.index", _external=True, **status))

    try:
        company.delete_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.company.index", _external=True, **status))

    try:
        db.session.delete(company)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.company.index", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Company deleted successfully!").get_status()
    return redirect(url_for("admin.company.index", _external=True, **status))
