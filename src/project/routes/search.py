from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    Geography,
    Industry,
    Round,
    SearchHistory,
    entity_search,
)
from ..schemas.user import SearchHistorySchema
from ..utils.decorators import (
    check_user_info_complete,
    check_verification,
)
from ..utils.enums import SearchHistoryType
from ..utils.funcs import generate_pagination
from ..utils.posthog import capture_event, capture_page_visit

search = Blueprint("search", __name__)


@search.get("/search/investors/<search>")
@login_required
@check_verification
def search_investors_onboarding(search):
    try:
        result = entity_search.get_search(
            query=search,
            entity_type="person",
            per_page=18,
        )
    except Exception:
        result = {"hits": []}

    entities = [
        {
            "id": hit.get("document", {}).get("db_id"),
            "name": hit.get("document", {}).get("name"),
        }
        for hit in result.get("hits", [])
    ]
    return jsonify({"investors": entities})


@search.get("/search/investment-firms/<search>")
@login_required
@check_verification
def search_investment_firms_onboarding(search):
    try:
        result = entity_search.get_search(
            query=search,
            entity_type="org",
            per_page=18,
        )
    except Exception:
        result = {"hits": []}

    entities = [
        {
            "id": hit.get("document", {}).get("db_id"),
            "name": hit.get("document", {}).get("name"),
        }
        for hit in result.get("hits", [])
    ]
    return jsonify({"investors": entities})


@search.get("/search/<search_input>")
@login_required
@check_verification
def search_entities(search_input):
    try:
        result = entity_search.get_search(
            query=search_input,
            per_page=18,
        )
    except Exception:
        result = {"hits": []}

    combined_results = [
        {
            "id": hit.get("document", {}).get("db_id"),
            "name": hit.get("document", {}).get("name"),
            "type": hit.get("document", {}).get("entity_type"),
        }
        for hit in result.get("hits", [])
    ]
    return jsonify({"results": combined_results})


@search.route("/search", methods=["GET", "POST"])
def investor_search():
    capture_page_visit("investor_search")

    if next_url := request.args.get("next"):
        return redirect(next_url)

    search_string = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)

    stages = []
    for round_name in request.args.getlist("round"):
        if Round.get_by_name(round_name):
            stages.append(round_name)

    industries = []
    for industry_name in request.args.getlist("industry"):
        if Industry.get_by_name(industry_name):
            industries.append(industry_name)

    geo_slugs = []
    for geo_slug in request.args.getlist("country"):
        geo_slugs.append(geo_slug)

    try:
        result = entity_search.get_search(
            query=search_string or "*",
            entity_type="person",
            industries=industries or None,
            stages=stages or None,
            geographies=geo_slugs or None,
            check_size_min=request.args.get("min_investment", type=int),
            check_size_max=request.args.get("max_investment", type=int),
            sort_by=request.args.get("sort_field"),
            sort_desc=request.args.get("descending", False, type=bool),
            page=page,
            per_page=18,
        )
    except Exception:
        result = {"found": 0, "page": page, "hits": [], "pages": 1}

    found = result.get("found", 0)
    result_page = int(result.get("page", page))
    per_page = 18
    pages = found // per_page + (1 if found % per_page else 0)
    pagination = generate_pagination(result_page, max(pages, 1))

    investors = [
        {
            "id": hit.get("document", {}).get("db_id"),
            "name": hit.get("document", {}).get("name"),
            "slug": hit.get("document", {}).get("slug"),
            "about": hit.get("document", {}).get("about"),
            "headline": hit.get("document", {}).get("headline"),
            "org_name": hit.get("document", {}).get("org_name"),
            "industries": hit.get("document", {}).get("industries", []),
            "stages": hit.get("document", {}).get("stages", []),
            "geographies": hit.get("document", {}).get("geographies", []),
            "check_size_min": hit.get("document", {}).get("check_size_min"),
            "check_size_max": hit.get("document", {}).get("check_size_max"),
            "n_investments": hit.get("document", {}).get("n_investments"),
            "n_exits": hit.get("document", {}).get("n_exits"),
        }
        for hit in result.get("hits", [])
    ]

    if search_string and current_user.is_authenticated:
        try:
            new_search_history = SearchHistory(
                user_id=current_user.id, query=search_string, type=SearchHistoryType.INVESTOR
            )
            db.session.add(new_search_history)
            db.session.commit()

            capture_event(
                event="search_investor_performed",
                properties={
                    "search_query": search_string,
                    "user_id": current_user.id,
                    "page": page,
                    "filters": {
                        "stages": stages,
                        "industries": industries,
                        "geographies": geo_slugs,
                    },
                    "sort_field": request.args.get("sort_field"),
                    "descending": request.args.get("descending", False, type=bool),
                },
                distinct_id=current_user.id,
            )

        except IntegrityError:
            db.session.rollback()

    geographies = db.session.scalars(db.select(Geography)).all()

    return render_template(
        "search.html",
        investors=investors,
        query=search_string,
        fields={
            "n_investments": "Number of Investments",
            "n_exits": "Number of Exits",
            "check_size_min": "Minimum Investment",
            "check_size_max": "Maximum Investment",
        },
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        industry_list=Industry.get_all(),
        round_list=Round.get_all(),
        geographies=geographies,
        user=current_user if current_user.is_authenticated else None,
        type=SearchHistoryType.INVESTOR.value.lower(),
    )


@search.route("/search/investment-firms", methods=["GET", "POST"])
def search_investment_firms():
    capture_page_visit("investment_firm_search")

    search_string = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)

    stages = []
    for round_name in request.args.getlist("round"):
        if Round.get_by_name(round_name):
            stages.append(round_name)

    industries = []
    for industry_name in request.args.getlist("industry"):
        if Industry.get_by_name(industry_name):
            industries.append(industry_name)

    geo_slugs = []
    for geo_slug in request.args.getlist("country"):
        geo_slugs.append(geo_slug)

    try:
        result = entity_search.get_search(
            query=search_string or "*",
            entity_type="org",
            industries=industries or None,
            stages=stages or None,
            geographies=geo_slugs or None,
            check_size_min=request.args.get("min_investment", type=int),
            check_size_max=request.args.get("max_investment", type=int),
            sort_by=request.args.get("sort_field"),
            sort_desc=request.args.get("descending", False, type=bool),
            page=page,
            per_page=18,
        )
    except Exception:
        result = {"found": 0, "page": page, "hits": [], "pages": 1}

    found = result.get("found", 0)
    result_page = int(result.get("page", page))
    per_page = 18
    pages = found // per_page + (1 if found % per_page else 0)
    pagination = generate_pagination(result_page, max(pages, 1))

    investment_firms = [
        {
            "id": hit.get("document", {}).get("db_id"),
            "name": hit.get("document", {}).get("name"),
            "slug": hit.get("document", {}).get("slug"),
            "about": hit.get("document", {}).get("about"),
            "industries": hit.get("document", {}).get("industries", []),
            "stages": hit.get("document", {}).get("stages", []),
            "geographies": hit.get("document", {}).get("geographies", []),
            "check_size_min": hit.get("document", {}).get("check_size_min"),
            "check_size_max": hit.get("document", {}).get("check_size_max"),
            "n_investments": hit.get("document", {}).get("n_investments"),
            "n_exits": hit.get("document", {}).get("n_exits"),
            "person_names": hit.get("document", {}).get("person_names", []),
        }
        for hit in result.get("hits", [])
    ]

    if search_string and current_user.is_authenticated:
        try:
            new_search_history = SearchHistory(
                user_id=current_user.id, query=search_string, type=SearchHistoryType.INVESTMENT_FIRM
            )
            db.session.add(new_search_history)
            db.session.commit()

            capture_event(
                event="search_investment_firm_performed",
                properties={
                    "search_query": search_string,
                    "user_id": current_user.id,
                    "page": page,
                    "filters": {
                        "stages": stages,
                        "industries": industries,
                        "geographies": geo_slugs,
                    },
                    "sort_field": request.args.get("sort_field"),
                    "descending": request.args.get("descending", False, type=bool),
                },
                distinct_id=current_user.id,
            )

        except IntegrityError:
            db.session.rollback()

    geographies = db.session.scalars(db.select(Geography)).all()

    return render_template(
        "search_investment_firms.html",
        investment_firms=investment_firms,
        query=search_string,
        fields={
            "n_investments": "Number of Investments",
            "n_exits": "Number of Exits",
            "check_size_min": "Minimum Investment",
            "check_size_max": "Maximum Investment",
            "n_employees": "Number of Employees",
        },
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        industry_list=Industry.get_all(),
        round_list=Round.get_all(),
        geographies=geographies,
        type=SearchHistoryType.INVESTMENT_FIRM.value.lower().replace("_", ""),
        user=current_user if current_user.is_authenticated else None,
    )


@search.get("/search-history")
@login_required
@check_user_info_complete
@check_verification
def get_search_histories():
    search_type = request.args.get("type")
    search_string = request.args.get("search", "").strip()
    page = request.args.get("page", default=1, type=int)
    limit = request.args.get("limit", default=5, type=int)
    if limit > 100:
        limit = 100
    offset = (page - 1) * limit
    search_histories = []

    match search_type:
        case "investor":
            type = SearchHistoryType.INVESTOR
        case "investmentfirm":
            type = SearchHistoryType.INVESTMENT_FIRM
        case "company":
            type = SearchHistoryType.COMPANY
        case _:
            type = False

    db_search_histories = SearchHistory.paginate_history(
        user=current_user, search_type=type, search_string=search_string, offset=offset, limit=limit
    )

    search_histories = [
        SearchHistorySchema.model_validate(history, from_attributes=True).model_dump()
        for history in db_search_histories
    ]

    day_list = []
    for history in search_histories:
        day = history["date"]
        if not any(day == day_item["day"] for day_item in day_list):
            day_list.append({"day": day, "histories": []})
        for day_item in day_list:
            if day_item["day"] == day:
                day_item["histories"].append(history)

    return jsonify(day_list)


@search.get("/history/types")
@login_required
@check_user_info_complete
@check_verification
def get_history_types():
    types = [
        {"value": type.value.replace("_", ""), "readable": type.name.title().replace("_", " ")}
        for type in SearchHistoryType
    ]
    return jsonify(types)


@search.get("/history")
@login_required
@check_user_info_complete
@check_verification
def get_full_search_history():
    return render_template("history.html")


@search.post("/history/delete")
@login_required
@check_user_info_complete
@check_verification
def delete_histories():
    form_data = request.get_json()
    history_ids = form_data.get("ids", [])

    if not history_ids:
        return jsonify({"error": "No history IDs provided"}), 400

    try:
        history_ids = [int(id) for id in history_ids]

        stmt = db.select(SearchHistory.id).where(
            SearchHistory.id.in_(history_ids), SearchHistory.user_id == current_user.id
        )
        valid_ids = [str(id[0]) for id in db.session.execute(stmt).all()]

        delete_stmt = db.delete(SearchHistory).where(SearchHistory.id.in_(valid_ids))
        db.session.execute(delete_stmt)
        db.session.commit()

        return jsonify({"message": "Successfully deleted entries", "deleted_ids": valid_ids}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete items: {str(e)}"}), 500
