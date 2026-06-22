from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    SearchHistory,
    entity_search,
)
from ..schemas.user import SearchHistorySchema
from ..utils.decorators import (
    check_user_info_complete,
    check_verification,
)
from ..utils.enums import SearchHistoryType

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
    """Legacy route — 301 redirect to /investors, preserving query string."""
    qs = request.query_string.decode()
    target = "/investors"
    if qs:
        target = f"{target}?{qs}"
    return redirect(target, 301)


@search.route("/search/investment-firms", methods=["GET", "POST"])
def search_investment_firms():
    """Legacy route — 301 redirect to /firms, preserving query string."""
    qs = request.query_string.decode()
    target = "/firms"
    if qs:
        target = f"{target}?{qs}"
    return redirect(target, 301)


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
