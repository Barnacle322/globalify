from collections import OrderedDict, defaultdict

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import or_, select

from ...extensions import db
from ...models import (
    Industry,
    Investor,
    InvestorBackup,
    InvestorOriginPoint,
    NotableInvestment,
    Round,
    User,
    entity_search,
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
        investments_by_round={},
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
    try:
        investor.upsert_data()  # TODO(phase-2): rewire onto entity model
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.update_investor_view", id=id, _external=True, **status))

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
        try:
            investor.upsert_data()  # TODO(phase-2): rewire onto entity model
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("admin.investor.update_investor_view", id=id, _external=False, **status))
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

    twitter = form_data.get("twitter") or None
    if isinstance(twitter, str) and "x.com" in twitter:
        slug = twitter.split("/")[-1]
        twitter = f"https://twitter.com/{slug}"

    investor = Investor(
        first_name=first_name,
        last_name=form_data.get("last_name"),
        slug=form_data.get("slug") or None,
        firm_name=form_data.get("firm_name") or None,
        position=form_data.get("position") or None,
        about=form_data.get("about") or None,
        website=form_data.get("website") or None,
        linkedin=form_data.get("linkedin") or None,
        twitter=twitter,
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
@admin_only
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

    base_query = db.select(Investor)
    conditions = []

    if "check_about" in active_filters:
        conditions.append((Investor.about.is_(None)) | (Investor.about == ""))

    if "check_email" in active_filters:
        conditions.append((Investor.email.is_(None)) | (Investor.email == ""))

    if "check_twitter" in active_filters:
        conditions.append((Investor.twitter.is_(None)) | (Investor.twitter == ""))

    if "check_linkedin" in active_filters:
        conditions.append((Investor.linkedin.is_(None)) | (Investor.linkedin == ""))

    if "check_website" in active_filters:
        conditions.append((Investor.website.is_(None)) | (Investor.website == ""))

    if conditions:
        base_query = base_query.where(or_(*conditions))

    pagination = db.paginate(base_query, page=page, per_page=per_page, error_out=False)

    investors_data = []
    for investor in pagination.items:
        investors_data.append(
            {
                "id": investor.id,
                "name": investor.full_name,
                "about": investor.about,
                "email": investor.email,
                "twitter": investor.twitter,
                "linkedin": investor.linkedin,
                "website": investor.website,
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


@investor.get("/duplicates/")
@admin_only
def duplicates():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template(
        "admin/duplicates_investors.html",
        status_type=status_type,
        msg=msg,
    )


# NOTE
# Default list of available params contains in Duplicate.js in data-return{}
@investor.post("/get/duplicates/")
@admin_only
def get_duplicates():
    batch_size = 1000
    offset = 0

    form_data = request.get_json()
    selected_fields = form_data.get("selected_params", [])

    query_params = request.args
    page = query_params.get("page", 1, type=int)
    per_page = query_params.get("per_page", 4, type=int)

    fields_order = [
        "id",
        "first_name",
        "last_name",
        "email",
        "slug",
        "firm_name",
        "about",
        "position",
        "website",
        "linkedin",
        "twitter",
        "phone_number",
        "n_investments",
        "n_exits",
        "min_investment",
        "max_investment",
        "location",
        "is_public",
        "is_approved",
        "rounds",
        "industries",
    ]

    # confidence_threshold = 1
    # default_weight = 1
    # weight_mapping = {
    #     "first_name": 1,
    #     "last_name": 1,
    #     "firm_name": 1,
    #     "email": 1,
    #     "linkedin": 1,
    #     "twitter": 1,
    #     "phone_number": 1,
    # }

    try:
        investors = db.session.query(Investor).order_by(Investor.id).offset(offset).limit(batch_size).all()
        duplicate_groups = defaultdict(list)

        for investor in investors:
            if selected_fields:
                key_parts = []
                for field in selected_fields:
                    value = getattr(investor, field, None)
                    if value not in (None, ""):
                        key_parts.append(str(value))

                if not key_parts:
                    continue
                key = "|".join(key_parts)
            else:
                key = ""

            investor_data = OrderedDict()
            for field in fields_order:
                value = getattr(investor, field)

                if field == "rounds":
                    value = [{"id": round.id, "name": str(round)} for round in value] if value else []
                elif field == "industries":
                    value = [{"id": industry.id, "name": str(industry)} for industry in value] if value else []
                investor_data[field] = value

            duplicate_groups[key].append(investor_data)

        offset += batch_size

    except Exception as e:
        print(f"Error fetching investors at offset {offset}: {e}")

    # def calculate_priority_score(investor1, investor2, selected_fields):
    #     score = 0
    #     for field in selected_fields:
    #         weight = weight_mapping.get(field, default_weight)
    #         value1 = investor1.get(field)
    #         value2 = investor2.get(field)
    #         if value1 and value2 and value1 == value2:
    #             score += weight
    #     return score

    duplicates = []
    for investors in duplicate_groups.values():
        if len(investors) <= 1:
            continue
        for i, inv1 in enumerate(investors[:-1]):
            for inv2 in investors[i + 1 :]:
                # score = calculate_priority_score(inv1, inv2, selected_fields)
                # if score >= confidence_threshold:
                score = sum(1 for field in fields_order if inv1[field] and inv2[field] and inv1[field] == inv2[field])
                duplicates.append({"investor_a": inv1, "investor_b": inv2, "score": score})

    duplicates.sort(key=lambda x: x["score"], reverse=True)  # Duplicates with Most Matched Parameters Positioned Higher

    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    page_duplicates = duplicates[start_index:end_index]

    pagination = generate_pagination(page, int(len(duplicates) / per_page), per_page)
    pagination["pages"] = list(pagination["pages"])

    return {"comparisons": page_duplicates, "pagination": pagination}


@investor.post("/merge")
@admin_only
def merge_investors():
    form_data = request.get_json()

    investor = Investor(
        first_name=form_data.get("first_name"),
        last_name=form_data.get("last_name"),
        firm_name=form_data.get("firm_name") or None,
        position=form_data.get("position") or None,
        about=form_data.get("about") or None,
        website=form_data.get("website") or None,
        linkedin=form_data.get("linkedin") or None,
        twitter=form_data.get("twitter"),
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
        # user=user,
    )

    try:
        db.session.add(investor)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.create_investor_view", _external=True, **status))

    investor.set_slug()

    try:
        investor.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.investor.create_investor_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor created successfully!").get_status()

    return redirect(url_for("admin.investor.duplicates", _external=False))


@investor.get("/funding-rounds")
@admin_only
def get_funding_rounds():
    return {"funding_rounds": []}
