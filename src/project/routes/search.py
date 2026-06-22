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
    Country,
    Industry,
    InvestmentFirm,
    Investor,
    Round,
    SearchHistory,
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
    result = Investor.get_search(
        query_string=search,
        query_by=["name"],
        page=1,
        per_page=18,
    )

    return jsonify({"investors": result.get("investors")})


@search.get("/search/investment-firms/<search>")
@login_required
@check_verification
def search_investment_firms_onboarding(search):
    result = InvestmentFirm.get_search(
        query_string=search,
        query_by=["name"],
        page=1,
        per_page=18,
    )

    return jsonify({"investors": result.get("investment_firms")})


@search.get("/search/<search_input>")
@login_required
@check_verification
def search_entities(search_input):
    # Search investors
    investor_result = Investor.get_search(
        query_string=search_input,
        query_by=["name"],
        page=1,
        per_page=18,
    )
    investors = investor_result.get("investors", [])

    # Search investment firms
    investment_firm_result = InvestmentFirm.get_search(
        query_string=search_input,
        query_by=["name"],
        page=1,
        per_page=18,
    )
    investment_firms = investment_firm_result.get("investment_firms", [])

    combined_results = [
        {"id": investor.get("id"), "name": investor.get("name"), "type": "investor"} for investor in investors
    ] + [{"id": firm.get("id"), "name": firm.get("name"), "type": "investment_firm"} for firm in investment_firms]

    return jsonify({"results": combined_results})


@search.route("/search", methods=["GET", "POST"])
def investor_search():
    capture_page_visit("investor_search")

    if next_url := request.args.get("next"):
        return redirect(next_url)

    search_string = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)

    rounds = []
    for round_name in request.args.getlist("round"):
        if round_object := Round.get_by_name(round_name):
            rounds.append(round_object.name)

    industries = []
    for industry_name in request.args.getlist("industry"):
        if industry_object := Industry.get_by_name(industry_name):
            industries.append(industry_object.name)

    countries = []
    for country_name in request.args.getlist("country"):
        if country_object := Country.get_by_name(country_name):
            countries.append(country_object.name)

    result = Investor.get_search(
        query_string=search_string,
        query_by=[
            "location",
            "country",
            "rounds",
            "industries",
            "embedding",
            "notable_investments",
            "name",
            "firm_name",
            "position",
        ],
        sort_by=request.args.get("sort_field", "db_id"),
        sort_desc=request.args.get("descending", False, type=bool),
        rounds=rounds,
        industries=industries,
        rounds_exclusive=request.args.get("rounds_exclusive", False, type=bool),
        industries_exclusive=request.args.get("industries_exclusive", False, type=bool),
        min_investment=request.args.get("min_investment", type=int),
        max_investment=request.args.get("max_investment", type=int),
        page=page,
        per_page=18,
        countries=countries,
        is_public=True,
        is_approved=True,
    )

    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    if search_string != "" and current_user.is_authenticated:
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
                        "rounds": rounds,
                        "industries": industries,
                        "countries": countries,
                    },
                    "sort_field": request.args.get("sort_field", "db_id"),
                    "descending": request.args.get("descending", False, type=bool),
                },
                distinct_id=current_user.id,
            )

        except IntegrityError:
            db.session.rollback()

    return render_template(
        "search.html",
        investors=result.get("investors"),
        query=search_string,
        fields={
            "n_investments": "Number of Investments",
            "n_exits": "Number of Exits",
            "min_investment": "Minimum Investment",
            "max_investment": "Maximum Investment",
        },
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        industry_list=Industry.get_all(),
        round_list=Round.get_all(),
        countries=Country.get_all(),
        user=current_user if current_user.is_authenticated else None,
        type=SearchHistoryType.INVESTOR.value.lower(),
    )


@search.route("/search/investment-firms", methods=["GET", "POST"])
def search_investment_firms():
    capture_page_visit("investment_firm_search")

    search_string = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)

    rounds = []
    for round_name in request.args.getlist("round"):
        if round_object := Round.get_by_name(round_name):
            rounds.append(round_object.name)

    industries = []
    for industry_name in request.args.getlist("industry"):
        if industry_object := Industry.get_by_name(industry_name):
            industries.append(industry_object.name)

    countries = []
    for country_name in request.args.getlist("country"):
        if country_object := Country.get_by_name(country_name):
            countries.append(country_object.name)

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
        sort_by=request.args.get("sort_field", "db_id"),
        sort_desc=request.args.get("descending", False, type=bool),
        rounds=rounds,
        industries=industries,
        rounds_exclusive=request.args.get("rounds_exclusive", False, type=bool),
        industries_exclusive=request.args.get("industries_exclusive", False, type=bool),
        min_investment=request.args.get("min_investment", type=int),
        max_investment=request.args.get("max_investment", type=int),
        page=page,
        per_page=18,
        countries=countries,
        is_public=True,
    )
    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    if search_string != "" and current_user.is_authenticated:
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
                        "rounds": rounds,
                        "industries": industries,
                        "countries": countries,
                    },
                    "sort_field": request.args.get("sort_field", "db_id"),
                    "descending": request.args.get("descending", False, type=bool),
                },
                distinct_id=current_user.id,
            )

        except IntegrityError:
            db.session.rollback()

    return render_template(
        "search_investment_firms.html",
        investment_firms=result.get("investment_firms"),
        query=search_string,
        fields={
            "n_investments": "Number of Investments",
            "n_exits": "Number of Exits",
            "min_investment": "Minimum Investment",
            "max_investment": "Maximum Investment",
            "n_employees": "Number of Employees",
        },
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        industry_list=Industry.get_all(),
        round_list=Round.get_all(),
        countries=Country.get_all(),
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
