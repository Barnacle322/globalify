import json
import os
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta

import requests
from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    ClaimRequest,
    ClaimVerification,
    Company,
    CompanyBookmark,
    Country,
    Industry,
    InvestmentFirm,
    InvestmentFirmBookmark,
    Investor,
    InvestorBookmark,
    InvestorOriginPoint,
    Notification,
    Round,
    User,
    UserCompany,
    UserInfo,
    UserPayment,
)
from ..schemas.investor import (
    InvestmentFirmBookmarkSchema,
    InvestmentFirmSchema,
    InvestorBookmarkSchema,
    InvestorSchema,
)
from ..schemas.notification import NotificationItem, NotificationLayout
from ..schemas.user import CompanySchema
from ..utils.decorators import check_user_info_complete, check_verification
from ..utils.enums import Events, NotificationType, Status, StatusType
from ..utils.errors.error_messages import (
    CLAIM_REQUEST_ALREADY_SUBMITTED,
    EXPIRED_CODE,
    INVALID_CODE,
    INVALID_EMAIL,
    INVESTOR_ALREADY_CLAIMED,
    NOT_AUTHORIZED,
)
from ..utils.google_helpers.google_pubsub import send_event
from ..utils.parse_medium import parse_medium_html
from ..utils.suggestion import COMPANY_WEIGHTS, WEIGHTS, check_weights

main = Blueprint("main", __name__)


def generate_pagination(current_page: int, total_pages: int, around_count: int = 2) -> dict:
    start_pages = range(1, min(3, total_pages + 1))
    around_pages = range(max(1, current_page - around_count), min(current_page + around_count + 1, total_pages + 1))
    end_pages = range(max(current_page + around_count + 1, total_pages - 1), total_pages + 1)
    pages = list(start_pages)

    if not pages:
        return {
            "current_page": 0,
            "prev": 0,
            "next": 0,
            "pages": [],
            "has_other_pages": False,
            "has_prev": False,
            "has_next": False,
        }

    if around_pages and around_pages[0] - pages[-1] > 1:
        pages.append(0)
    pages.extend(p for p in around_pages if p not in pages)
    if end_pages and end_pages[0] - pages[-1] > 1:
        pages.append(0)
    pages.extend(p for p in end_pages if p not in pages)

    return {
        "current_page": current_page,
        "prev": max(1, current_page - 1),
        "next": min(current_page + 1, total_pages),
        "last_page": total_pages,
        "pages": around_pages,
        "has_other_pages": bool(len(around_pages) > 1),
        "has_prev": bool(current_page > 1),
        "has_next": bool(current_page < total_pages),
    }


@main.get("/")
def index():
    posts = parse_medium_html()
    return render_template("index.html", posts=posts)


@main.get("/faq")
def faq():
    return render_template("faq.html")


@main.get("/about/eric")
def eric():
    return render_template("eric.html")


@main.get("/about/jennifer")
def jennifer():
    return render_template("jennifer.html")


@main.get("/about/arstan")
def arstan():
    return render_template("arstan.html")


@main.route("/pricing")
def pricing():
    return render_template("pricing.html")


@main.route("/about")
def about():
    return render_template("about.html")


@main.route("/superconnect")
def superconnect():
    return render_template("superconnect.html")


@main.route("/docs")
@main.route("/jobs")
@main.route("/partners")
@main.route("/help")
@main.route("/investor-database")
@main.route("/startup-database")
@main.route("/digest")
@main.route("/data-request")
def construction():
    return render_template("construction.html")


@main.route("/terms-of-service")
def terms_of_service():
    return render_template("terms_of_service.html")


@main.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html")


@main.route("/suggestions")
@login_required
@check_user_info_complete
@check_verification
def get_suggestions():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

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
            user=authenticated_user,
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


@main.route("/suggestions/investment-firms")
@login_required
@check_user_info_complete
@check_verification
def get_suggestion_investment_firms():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

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
            user=authenticated_user,
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


@main.route("/suggestions/companies")
@login_required
@check_user_info_complete
@check_verification
def get_suggestion_companies():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

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
        companies=Company.get_suggestions(investor=Investor.get_by_user_id(authenticated_user.id), quantity=15),
        access=access,
    )


@main.route("/search/companies", methods=["GET", "POST"])
@login_required
@check_user_info_complete
@check_verification
def search_companies():
    search_string = request.args.get("search", "")
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
        per_page=9,
        countries=request.args.getlist("country"),
        is_public=True,
    )

    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))
    return render_template(
        "search_companies.html",
        companies=result.get("companies"),
        query=search_string,
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        industry_list=Industry.get_all(),
        round_list=Round.get_all(),
        countries=Country.get_all(),
        bookmark_ids=CompanyBookmark.get_id_list(current_user.id),
    )


@main.route("/search/investment-firms", methods=["GET", "POST"])
@login_required
@check_user_info_complete
@check_verification
def search_investment_firms():
    search_string = request.args.get("search", "")
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
        per_page=9,
        countries=countries,
    )
    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

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
    )


@main.get("/investment-firm/bookmarks")
@login_required
@check_user_info_complete
@check_verification
def get_investment_firm_bookmark_ids():
    bookmarks_ids = InvestmentFirmBookmark.get_id_list(current_user.id)
    return jsonify({"bookmark_ids": bookmarks_ids})


@main.route("/search", methods=["GET", "POST"])
@login_required
@check_user_info_complete
@check_verification
def search():
    if next_url := request.args.get("next"):
        return redirect(next_url)

    search_string = request.args.get("search", "")
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
        per_page=9,
        countries=countries,
    )

    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

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
        user=current_user,
    )


@main.get("/investor/bookmarks")
@login_required
@check_user_info_complete
@check_verification
def get_investor_bookmark_ids():
    bookmarks_ids = InvestorBookmark.get_id_list(current_user.id)
    return jsonify({"bookmark_ids": bookmarks_ids})


@main.get("/company/bookmarks")
@login_required
@check_user_info_complete
@check_verification
def get_company_bookmark_ids():
    bookmarks_ids = CompanyBookmark.get_id_list(current_user.id)
    return jsonify({"bookmark_ids": bookmarks_ids})


@main.get("/demo_search")
def demo_search():
    result = Investor.get_search(
        query_string=request.args.get("search", ""),
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
        page=1,
        per_page=9,
    )

    return jsonify(result.get("investors"))


@main.route("/investor/<slug>")
@login_required
@check_user_info_complete
@check_verification
def investor_slug(slug):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("main.search"))

    return render_template("investor.html", investor=investor, user=current_user, status_type=status_type, msg=msg)


@main.get("/investor/<slug>/claim")
@login_required
def claiming_types_view(slug):
    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("main.search"))

    if email := investor.email:
        email = email[:3] + "*" * (len(email) - 6) + email[-3:]
        investor.email = email

    return render_template("claiming/index.html", investor=investor)


@main.get("/investor/<slug>/claim/manual")
@login_required
def claiming_manual_view(slug):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("main.search"))

    captcha_site_key = os.getenv("_GOOGLE_RECAPTCHA_SITE_KEY_DEV")

    return render_template(
        "claiming/manual.html",
        investor=investor,
        status_type=status_type,
        captcha_site_key=captcha_site_key,
        msg=msg,
    )


@main.post("/investor/<slug>/claim/manual")
@login_required
def claiming_manual(slug):
    form_data = request.get_json()
    email = form_data.get("email")
    recaptcha_response = form_data.get("recaptcha")

    secret_key = os.getenv("_GOOGLE_RECAPTCHA_SECRET_KEY_DEV")
    captcha_verification_url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {"secret": secret_key, "response": recaptcha_response}
    response = requests.post(captcha_verification_url, data=payload)
    result = response.json()

    if not result.get("success"):
        status = Status(StatusType.ERROR, "CAPTCHA verification failed.").get_status()
        return redirect(url_for("main.claiming_manual_view", slug=slug, _external=False, **status))

    existing_claim = Investor.get_by_user_id(current_user.id)
    if existing_claim:
        status = Status(StatusType.ERROR, "You can't claim another investor account!").get_status()
        return redirect(url_for("main.claiming_manual_view", slug=slug, _external=False, **status))

    investor = Investor.get_by_slug(slug)
    if not investor:
        return jsonify({"status": "error", "message": "Investor not found."}), 404

    claim_request = ClaimRequest.get_by_user_id(current_user.id)
    if claim_request:
        if claim_request.status == "pending":
            status = Status(StatusType.ERROR, CLAIM_REQUEST_ALREADY_SUBMITTED).get_status()
            return redirect(url_for("main.claiming_manual_view", slug=slug, _external=False, **status))
        elif claim_request.status == "approved":
            status = Status(StatusType.ERROR, INVESTOR_ALREADY_CLAIMED).get_status()
            return redirect(url_for("main.claiming_manual_view", slug=slug, _external=False, **status))

    claim_request = ClaimRequest(
        user_id=current_user.id,
        investor_id=investor.id,
        email=email,
    )
    db.session.add(claim_request)

    investor_point_origin = InvestorOriginPoint.get_by_investor_id(investor.id)
    if not investor_point_origin:
        investor_point_origin = InvestorOriginPoint(investor=investor)
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
    db.session.commit()

    status = Status(StatusType.SUCCESS, "Claim request submitted.").get_status()
    return redirect(url_for("main.investor_slug", slug=slug, _external=False, **status))


@main.get("/investor/<slug>/claim/email")
@login_required
def claiming_email_view(slug):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    captcha_site_key = os.getenv("_GOOGLE_RECAPTCHA_SITE_KEY_DEV")

    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("main.search"))

    return render_template(
        "claiming/email.html", investor=investor, status_type=status_type, msg=msg, captcha_site_key=captcha_site_key
    )


@main.post("/investor/<slug>/claim/email")
@login_required
def claiming_email(slug):
    form_data = request.get_json()
    recaptcha_response = form_data.get("recaptcha")

    secret_key = os.getenv("_GOOGLE_RECAPTCHA_SECRET_KEY_DEV")
    captcha_verification_url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {"secret": secret_key, "response": recaptcha_response}
    response = requests.post(captcha_verification_url, data=payload)
    result = response.json()

    if not result.get("success"):
        status = Status(StatusType.ERROR, "CAPTCHA verification failed.").get_status()
        return redirect(url_for("main.claiming_email_view", slug=slug, _external=False, **status))

    investor = Investor.get_by_slug(slug)
    if not investor or investor.user_id:
        return redirect(url_for("main.search"))

    existing_claim = Investor.get_by_user_id(current_user.id)
    if existing_claim:
        status = Status(StatusType.ERROR, "You can't claim another investor account!").get_status()
        return redirect(url_for("main.claiming_email_view", slug=slug, _external=False, **status))

    verification = ClaimVerification(user_id=current_user.id, investor_id=investor.id)
    db.session.add(verification)
    db.session.commit()

    send_event(
        "User wants to claim investor!",
        event_type=Events.INVESTOR_PROFILE_CLAIM_REQUEST.value,
        email=investor.email,
        investor_slug=slug,
        verification_token=verification.token,
    )

    status = Status(StatusType.SUCCESS, "Verification email sent.").get_status()
    return redirect(url_for("main.investor_slug", slug=slug, _external=False, **status))


@main.get("/investor/<slug>/claim/email/verify")
@login_required
def claim_verification_view(slug):
    verification_code = request.args.get("verification_code")

    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("main.search"))

    return render_template(
        "claiming/email_verification.html",
        investor=investor,
        verification_code=verification_code,
        status_type=status_type,
        msg=msg,
    )


@main.post("/investor/<slug>/claim/email/verify")
@login_required
def claim_verification(slug):
    form_data = request.get_json()
    verification_code = form_data.get("code")
    user_email = form_data.get("email")

    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("main.search"))

    claim_verification = ClaimVerification.get_by_token(verification_code)
    if not claim_verification:
        status = Status(StatusType.ERROR, INVALID_CODE).get_status()
        return redirect(url_for("main.claim_verification_view", slug=slug, _external=False, **status))

    if claim_verification.is_expired:
        status = Status(StatusType.ERROR, EXPIRED_CODE).get_status()
        return redirect(url_for("main.claim_verification_view", slug=slug, _external=False, **status))

    if user_email != current_user.email:
        status = Status(StatusType.ERROR, INVALID_EMAIL).get_status()
        return redirect(url_for("main.claim_verification_view", slug=slug, _external=False, **status))

    investor.user_id = current_user.id
    claim_verification.is_used = True

    investor_point_origin = InvestorOriginPoint.get_by_investor_id(investor.id)
    if not investor_point_origin:
        investor_point_origin = InvestorOriginPoint(investor=investor)
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

    db.session.commit()

    status = Status(StatusType.SUCCESS, "Investor claimed.").get_status()
    return redirect(url_for("main.investor_slug", slug=slug, _external=False, **status))


@main.get("/investor/<slug>/get")
@login_required
def get_investor(slug):
    user_payment = UserPayment.get_by_user_id(current_user.id)

    unpaid = False
    if current_user.is_admin:
        pass
    elif not user_payment:
        unpaid = True
    elif user_payment and not user_payment.is_active:
        unpaid = True

    investor = Investor.get_by_slug(slug) if not unpaid else Investor.get_by_slug_without_contacts(slug)
    if not investor:
        return jsonify({"status": "error", "message": "Investor not found."}), 404

    investor = InvestorSchema(
        id=investor.id,
        name=f"{investor.first_name} {investor.last_name}",
        slug=investor.slug,
        firm_name=investor.firm_name,
        about=investor.about,
        position=investor.position,
        website=investor.website,
        linkedin=investor.linkedin,
        twitter=investor.twitter,
        email=investor.email,
        phone_number=investor.phone_number,
        n_investments=investor.n_investments,
        n_exits=investor.n_exits,
        min_max_investment=investor.min_max_investment,
        location=investor.location,
        notable_investments=[{"id": ni.id, "name": ni.name} for ni in investor.notable_investments],
        rounds=[{"id": r.id, "name": r.name} for r in investor.rounds],
        industries=[{"id": i.id, "name": i.name} for i in investor.industries],
        user_id=investor.user_id,
    )

    is_bookmarked = InvestorBookmark.exists(investor.id, current_user.id)
    return jsonify({"investor": investor.model_dump(), "unpaid": unpaid, "isBookmarked": is_bookmarked})


@main.get("/investment-firm/<slug>")
@login_required
@check_user_info_complete
@check_verification
def get_investment_firm(slug):
    investment_firm_model = InvestmentFirm.get_by_slug(slug)

    if not investment_firm_model:
        return jsonify({"status": "error", "message": "Investment Firm not found."}), 404

    investment_firm = InvestmentFirmSchema(
        id=investment_firm_model.id,
        name=investment_firm_model.name,
        slug=investment_firm_model.slug,
        about=investment_firm_model.about,
        website=investment_firm_model.website,
        linkedin=investment_firm_model.linkedin,
        twitter=investment_firm_model.twitter,
        email=investment_firm_model.email,
        phone_number=investment_firm_model.phone_number,
        n_investments=investment_firm_model.n_investments,
        n_exits=investment_firm_model.n_exits,
        n_employees=investment_firm_model.n_employees,
        min_max_investment=investment_firm_model.min_max_investment,
        location=investment_firm_model.location,
        notable_investments=[{"id": ni.id, "name": ni.name} for ni in investment_firm_model.notable_investments],
        rounds=[{"id": r.id, "name": r.name} for r in investment_firm_model.rounds],
        industries=[{"id": i.id, "name": i.name} for i in investment_firm_model.industries],
    ).model_dump()

    is_bookmarked = InvestmentFirmBookmark.exists(investment_firm_model.id, current_user.id)
    return jsonify({"investment_firm": investment_firm, "isBookmarked": is_bookmarked})


@main.get("/company/<slug>")
@login_required
@check_user_info_complete
@check_verification
def get_company(slug):
    company_model = Company.get_by_slug(slug)

    if not company_model:
        return jsonify({"status": "error", "message": "Company not found."}), 404

    company = CompanySchema(
        id=company_model.id,
        name=company_model.name,
        slug=company_model.slug,
        description=company_model.description,
        number_of_employees=company_model.number_of_employees,
        website=company_model.website_url,
        linkedin=company_model.linkedin_url,
        instagram=company_model.instagram_url,
        twitter=company_model.twitter_url,
        picture_url=company_model.picture_url,
        country=company_model.country.name,
        preferred_round={"id": company_model.preferred_round.id, "name": company_model.preferred_round.name},
        industry={"id": company_model.industry.id, "name": company_model.industry.name},
    ).model_dump()
    is_bookmarked = CompanyBookmark.exists(company_model.id, current_user.id)

    return jsonify({"company": company, "isBookmarked": is_bookmarked})


@main.post("/investor/<int:investor_id>/bookmark")
@login_required
@check_user_info_complete
@check_verification
def toggle_bookmark_investor(investor_id):
    investor = Investor.get_by_id(int(investor_id))
    if not investor:
        return jsonify({"status": "error", "message": "Investor not found."}), 404

    bookmark = InvestorBookmark.get_by_id(investor.id, current_user.id)
    if bookmark:
        db.session.delete(bookmark)
        db.session.commit()
        return jsonify({"bookmarked": False}, 200)

    new_bookmark = InvestorBookmark(investor_id=investor.id, user_id=current_user.id)
    db.session.add(new_bookmark)
    db.session.commit()

    return jsonify({"bookmarked": True}, 200)


@main.post("/company/<int:company_id>/bookmark")
@login_required
@check_user_info_complete
@check_verification
def toggle_bookmark_company(company_id):
    company = Company.get_by_id(int(company_id))
    if not company:
        return jsonify({"status": "error", "message": "Company not found."}), 404

    bookmark = CompanyBookmark.get_by_ids(company.id, current_user.id)
    if bookmark:
        db.session.delete(bookmark)
        db.session.commit()
        return jsonify({"bookmarked": False}, 200)

    new_bookmark = CompanyBookmark(company_id=company.id, user_id=current_user.id)
    db.session.add(new_bookmark)
    db.session.commit()

    return jsonify({"bookmarked": True}, 200)


@main.get("/investors/bookmarks")
@login_required
@check_user_info_complete
@check_verification
def get_investor_bookmarks():
    user_id = current_user.id

    page = request.args.get("page", default=1, type=int)
    limit = 10
    offset = (page - 1) * limit

    investors = []
    bookmarks = InvestorBookmark.get_by_user_id(user_id, offset=offset, limit=limit)
    for db_investor in bookmarks:
        if not isinstance(db_investor, Investor):
            return jsonify({"status": "error", "message": "Investors not found."}), 404

        investor = InvestorBookmarkSchema(
            id=db_investor.id,
            name=f"{db_investor.first_name} {db_investor.last_name}",
            position=db_investor.position,
            firm_name=db_investor.firm_name,
            about=db_investor.about,
            twitter=db_investor.twitter,
            slug=db_investor.slug,
        )
        investors.append(json.loads(investor.model_dump_json()))

    return jsonify({"bookmarks": investors})


@main.get("/check-investor")
@login_required
def check_investor():
    autentication_user: User = current_user._get_current_object()  # type: ignore

    user_info = UserInfo.get_by_user_id(autentication_user.id)
    if not user_info:
        return jsonify({"status": "error", "message": "User Info not found."}), 404

    result = Investor.get_search(
        query_string=user_info.full_name,
        query_by=["name"],
        page=1,
        per_page=9,
    )

    return jsonify({"existing_investors": result.get("investors")})


@main.get("/search/investors/<search>")
@login_required
@check_verification
def search_investors(search):
    result = Investor.get_search(
        query_string=search,
        query_by=["name"],
        page=1,
        per_page=9,
    )

    return jsonify({"investors": result.get("investors")})


@main.get("/investment-firms/bookmarks")
@login_required
@check_user_info_complete
@check_verification
def get_investment_firms_bookmarks():
    user_id = current_user.id

    page = request.args.get("page", default=1, type=int)
    limit = 10
    offset = (page - 1) * limit

    investment_firms = []
    bookmarks = InvestmentFirmBookmark.get_by_user_id(user_id, offset=offset, limit=limit)
    for db_investment_firm in bookmarks:
        if not isinstance(db_investment_firm, InvestmentFirm):
            return jsonify({"status": "error", "message": "Investment Firms not found."}), 404

        investment_firm = InvestmentFirmBookmarkSchema(
            id=db_investment_firm.id,
            name=db_investment_firm.name,
            about=db_investment_firm.about,
            slug=db_investment_firm.slug,
        )
        investment_firms.append(json.loads(investment_firm.model_dump_json()))

    return jsonify({"bookmarks": investment_firms})


@main.route("/investment-firm/<slug>")
@login_required
@check_user_info_complete
@check_verification
def investment_firm_slug(slug):
    investment_firm = InvestmentFirm.get_by_slug(slug)
    if not investment_firm:
        return redirect(url_for("main.search"))

    return render_template("investment_firm.html", investment_firm=investment_firm, user=current_user)


@main.post("/investment-firm/<int:firm_id>/bookmark")
@login_required
@check_user_info_complete
@check_verification
def toggle_bookmark_investment_firm(firm_id):
    investment_firm = InvestmentFirm.get_by_id(int(firm_id))
    if not investment_firm:
        return jsonify({"status": "error", "message": "Investment Firm not found."}), 404

    bookmark = InvestmentFirmBookmark.get_by_id(investment_firm.id, current_user.id)
    if bookmark:
        db.session.delete(bookmark)
        db.session.commit()
        return jsonify({"bookmarked": False}, 200)

    new_bookmark = InvestmentFirmBookmark(investment_firm_id=investment_firm.id, user_id=current_user.id)
    db.session.add(new_bookmark)
    db.session.commit()

    return jsonify({"bookmarked": True}, 200)


@main.get("/notification/edit/<int:notification_id>")
@login_required
def update_notification(notification_id):
    notification = Notification.get_by_id(int(notification_id))
    if not notification:
        return redirect(url_for("main.search"))

    if notification.user_id != current_user.id:
        return redirect(url_for("main.search"))

    notification.is_read = True
    db.session.commit()

    return jsonify({"status": "success"}), 200


@main.get("/notifications")
@login_required
def get_notifications():
    page = request.args.get("page", default=1, type=int)
    limit = 10
    offset = (page - 1) * limit

    notifications = Notification.get_by_user_id(user_id=current_user.id, offset=offset, limit=limit)
    notifications = [notification.to_dict() for notification in notifications]

    return jsonify({"notifications": notifications})


@main.get("/notifications/archived")
@login_required
def get_read_notifications():
    page = request.args.get("page", default=1, type=int)
    limit = 10
    offset = (page - 1) * limit

    notifications = Notification.get_by_user_id(user_id=current_user.id, offset=offset, limit=limit, get_read=True)
    notifications = [notification.to_dict() for notification in notifications]

    return jsonify({"notifications": notifications})


@main.post("/notifications/mark-all-read")
@login_required
def mark_all_notifications_read():
    Notification.mark_notifications_as_read(user_id=current_user.id)

    return jsonify({"status": "success"}), 200


@main.post("/notification/mark-read/<int:notification_id>")
@login_required
def mark_notification_read(notification_id):
    notification = Notification.get_by_id(int(notification_id))
    if not notification:
        return jsonify({"status": "error", "message": "Notification not found."}), 404

    if notification.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Not authorized."}), 401

    notification.is_read = True
    db.session.commit()

    if item := notification.json_data.get("item"):
        url = item.get("url")
        if url:
            return redirect(url)

    return jsonify({"status": "success"}), 200


@main.route("/sitemap.xml")
def sitemap():
    pages = []
    ten_days_ago = (datetime.now() - timedelta(days=10)).date().isoformat()

    # Add static pages
    for rule in current_app.url_map.iter_rules():
        if "GET" in rule.methods and len(rule.arguments) == 0:  # type: ignore
            pages.append([rule.rule, ten_days_ago])

    # Add dynamic pages
    # pages.append(["/dynamic-page", ten_days_ago])

    # Create the XML sitemap
    root = ElementTree.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for page in pages:
        url = ElementTree.SubElement(root, "url")
        loc = ElementTree.SubElement(url, "loc")
        loc.text = page[0]
        lastmod = ElementTree.SubElement(url, "lastmod")
        lastmod.text = page[1]
        changefreq = ElementTree.SubElement(url, "changefreq")
        changefreq.text = "weekly"
        priority = ElementTree.SubElement(url, "priority")
        priority.text = "0.5"

    # Return the XML sitemap as a response
    sitemap_xml = ElementTree.tostring(root, encoding="utf-8")
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"

    return response


@main.route("/robots.txt")
def robots():
    robots_txt = "User-agent: *\nDisallow: /admin\nDisallow: /logout\nDisallow: /onboarding\nDisallow: /login-linkedin\nDisallow: /login-google\nDisallow: /google-oauth\nDisallow: /linkedin-oauth\n\nSitemap: https://globalify.xyz/sitemap.xml"
    response = make_response(robots_txt)
    response.headers["Content-Type"] = "text/plain"
    return response


@main.route("/health")
def health():
    return jsonify({"status": "ok"})


@main.errorhandler(400)
def bad_request(e):
    return render_template("errors/400.html"), 400


@main.errorhandler(401)
def unauthorized(e):
    status = Status(StatusType.ERROR, NOT_AUTHORIZED).get_status()
    return redirect(url_for("auth.login", _external=False, **status))


@main.errorhandler(403)
def forbidden(e):
    return render_template("errors/403.html"), 403


@main.errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html"), 404


@main.errorhandler(500)
def internal_server_error(e):
    return render_template("errors/500.html"), 500


@main.errorhandler(503)
def service_unavailable(e):
    return render_template("errors/503.html"), 503
