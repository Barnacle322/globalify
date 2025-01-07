from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    Company,
    Country,
    Industry,
    InvestmentFirm,
    InvestmentFirmBookmark,
    Investor,
    InvestorBookmark,
    Notification,
    Round,
    SearchHistory,
    User,
    UserCompany,
    UserPayment,
)
from ..schemas.notification import NotificationItem, NotificationLayout
from ..schemas.user import SearchHistorySchema
from ..utils.decorators import check_user_info_complete, check_verification
from ..utils.enums import NotificationType, SearchHistoryType
from ..utils.funcs import generate_pagination
from ..utils.posthog import capture_event, capture_page_visit
from ..utils.suggestion import COMPANY_WEIGHTS, WEIGHTS, check_weights

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
    if current_user.is_investor_mode:
        return redirect(url_for("search.search_companies"))
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


@search.route("/search/companies", methods=["GET", "POST"])
def search_companies():
    capture_page_visit("company_search")

    search_string = request.args.get("search", "").strip()
    page = request.args.get("page", 1, type=int)
    result = Company.get_search(
        query_string=search_string,
        query_by=[
            "country",
            "preferred_round",
            "industry",
            "embedding",
            "name",
        ],
        sort_by=request.args.get("sort_field", "db_id"),
        sort_desc=request.args.get("descending", False, type=bool),
        preferred_rounds=request.args.getlist("round"),
        industries=request.args.getlist("industry"),
        page=page,
        per_page=18,
        countries=request.args.getlist("country"),
        is_public=True,
    )

    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    if search_string != "" and current_user.is_authenticated:
        try:
            new_search_history = SearchHistory(
                user_id=current_user.id, query=search_string, type=SearchHistoryType.COMPANY
            )
            db.session.add(new_search_history)
            db.session.commit()

            capture_event(
                event="search_company_performed",
                properties={
                    "search_query": search_string,
                    "user_id": current_user.id,
                    "page": page,
                    "filters": {
                        "rounds": request.args.getlist("round"),
                        "industries": request.args.getlist("industry"),
                        "countries": request.args.getlist("country"),
                    },
                    "sort_field": request.args.get("sort_field", "db_id"),
                    "descending": request.args.get("descending", False, type=bool),
                },
                distinct_id=current_user.id,
            )

        except IntegrityError:
            db.session.rollback()

    return render_template(
        "search_companies.html",
        companies=result.get("companies"),
        query=search_string,
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        industry_list=Industry.get_all(),
        round_list=Round.get_all(),
        countries=Country.get_all(),
        type=SearchHistoryType.COMPANY.value.lower(),
        user=current_user if current_user.is_authenticated else None,
    )


@search.route("/suggestions")
@login_required
@check_user_info_complete
@check_verification
def get_suggestions():
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))
    access = True
    user_payment = UserPayment.get_by_user_id(current_user.id)
    if current_user.is_admin:
        access = True
    elif not user_payment:
        access = False
    elif user_payment and not user_payment.is_active:
        access = False

    user_company = UserCompany.get_primary_by_user_id(current_user.id)
    if not user_company:
        notification = Notification(
            user=current_user,
            json_data=NotificationLayout(
                title="Info",
                msg="It looks like you don't have a primary company set! Please set a primary company to access suggestions.",
                type="system",
                item=NotificationItem(
                    type=NotificationType.INFO.value,
                    url=url_for("settings.company_list_view"),
                ),
            ).model_dump(),
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("settings.company_list_view"))

    bookmarks = InvestorBookmark.get_id_list(current_user.id)
    company = Company.get_by_id(user_company.company_id)

    suggested_investors = Investor.get_suggestions(company=company, quantity=15)

    return render_template(
        "suggestions.html",
        investors=suggested_investors,
        access=access,
        bookmark_ids=bookmarks,
    )


@search.route("/suggestions/investment-firms")
@login_required
@check_user_info_complete
@check_verification
def get_suggestion_investment_firms():
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    access = True
    user_payment = UserPayment.get_by_user_id(current_user.id)
    if current_user.is_admin:
        access = True
    elif not user_payment:
        access = False
    elif user_payment and not user_payment.is_active:
        access = False

    user_company = UserCompany.get_primary_by_user_id(current_user.id)
    if not user_company:
        notification = Notification(
            user=current_user,
            json_data=NotificationLayout(
                title="Info",
                msg="Please mark a company as primary to access suggestions.",
                type="system",
                item=NotificationItem(type=NotificationType.INFO.value, url=url_for("settings.company_list_view")),
            ).model_dump(),
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(url_for("settings.company_list_view"))

    check_weights(WEIGHTS)

    return render_template(
        "suggestions_investment_firms.html",
        investment_firms=InvestmentFirm.get_suggestions(
            company=Company.get_by_id(user_company.company_id), quantity=15
        ),
        access=access,
        bookmark_ids=InvestmentFirmBookmark.get_id_list(current_user.id),
    )


@search.route("/suggestions/companies")
@login_required
@check_user_info_complete
@check_verification
def get_suggestion_companies():
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))
    access = True
    user_payment = UserPayment.get_by_user_id(current_user.id)
    if current_user.is_admin:
        access = True
    elif not user_payment:
        access = False
    elif user_payment and not user_payment.is_active:
        access = False

    check_weights(COMPANY_WEIGHTS)

    return render_template(
        "suggestions_companies.html",
        companies=Company.get_suggestions(investor=Investor.get_by_user_id(current_user.id), quantity=15),
        access=access,
    )


@search.get("/search-history")
@login_required
@check_user_info_complete
@check_verification
def get_search_histories():
    search_type = request.args.get("type")
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
        user=current_user, search_type=type, offset=offset, limit=limit
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


@search.get("/history")
@login_required
@check_user_info_complete
@check_verification
def get_full_search_history():
    return render_template("history.html")
