import json
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta

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
    Company,
    CompanyBookmark,
    Investment,
    InvestmentFirm,
    InvestmentFirmBookmark,
    Investor,
    InvestorBookmark,
    Notification,
    User,
    UserInfo,
    UserPayment,
)
from ..schemas.company import CompanyBookmarkSchema
from ..schemas.investment import InvestmentSchema
from ..schemas.investor import (
    InvestmentFirmBookmarkSchema,
    InvestmentFirmSchema,
    InvestorBookmarkSchema,
    InvestorSchema,
)
from ..schemas.user import CompanySchema
from ..utils.decorators import check_user_info_complete, check_verification
from ..utils.enums import Status, StatusType
from ..utils.errors.error_messages import (
    NOT_AUTHORIZED,
)
from ..utils.parse_medium import parse_medium_html

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return render_template("index.html", posts=parse_medium_html())


@main.get("/faq")
def faq():
    return render_template("faq.html")


@main.get("/eric")
@main.get("/ericfung")
@main.get("/ericclfung")
@main.get("/ceo")
def eric():
    return render_template("eric.html")


@main.get("/jennifer")
@main.get("/jenn")
@main.get("/jenniferchenglo")
@main.get("/jennifer-cheng-lo")
@main.get("/princess")
@main.get("/cgo")
def jennifer():
    return render_template("jennifer.html")


@main.get("/arstan")
@main.get("/cto")
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
@main.route("/terms-of-service")
def construction():
    return render_template("construction.html")


@main.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html")


@main.route("/investor/<slug>")
def investor_slug(slug):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investor = Investor.get_by_slug(slug)
    if not investor or not investor.is_public:
        return redirect(url_for("search.investor_search"))

    return render_template("investor.html", investor=investor, user=current_user, status_type=status_type, msg=msg)


@main.get("/investor/<slug>/get")
def get_investor(slug):
    unpaid = False

    if current_user.is_authenticated:
        user_payment = UserPayment.get_by_user_id(current_user.id)
        if current_user.is_admin:
            pass
        elif not user_payment:
            unpaid = True
        elif user_payment and not user_payment.is_active:
            unpaid = True
    else:
        unpaid = True

    investor = Investor.get_by_slug(slug) if not unpaid else Investor.get_by_slug_without_contacts(slug)
    if not investor:
        return jsonify({"status": "error", "message": "Investor not found."}), 404
    if not investor.is_public:
        return jsonify({"status": "error", "message": "Investor is not public."}), 404

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

    if current_user.is_authenticated:
        is_bookmarked = InvestorBookmark.exists(investor.id, current_user.id)
    else:
        is_bookmarked = False

    return jsonify({"investor": investor.model_dump(), "unpaid": unpaid, "isBookmarked": is_bookmarked})


@main.get("/investment/<int:investor_id>/get")
@login_required
@check_user_info_complete
@check_verification
def get_investment_investor(investor_id):
    model_investments = Investment.get_by_investor_id(investor_id)

    if not model_investments:
        return jsonify({"status": "error", "message": "Investments not found for this investor."}), 404

    investments = []

    for model_investment in model_investments:
        investment = InvestmentSchema(
            id=model_investment.id,
            name=model_investment.funding_round.company.name,
            round=model_investment.funding_round.round.name,
            amount=model_investment.amount,
            announced_date=model_investment.funding_round.announced_date.strftime("%b %d, %Y")
            if model_investment.funding_round.announced_date
            else None,
        )
        investments.append(json.loads(investment.model_dump_json()))

    return jsonify({"investments": investments, "n_of_investments": len(investments)})


@main.get("/check-investor")
@login_required
def check_investor():
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    user_info = UserInfo.get_by_user_id(current_user.id)
    if not user_info:
        return jsonify({"status": "error", "message": "User Info not found."}), 404

    result = Investor.get_search(
        query_string=user_info.full_name,
        query_by=["name"],
        page=1,
        per_page=18,
    )

    return jsonify({"existing_investors": result.get("investors")})


@main.post("/investor/<int:investor_id>/bookmark")
@login_required
@check_user_info_complete
@check_verification
def toggle_bookmark_investor(investor_id):
    investor = Investor.get_by_id(int(investor_id))
    if not investor or not investor.is_public:
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


@main.get("/bookmarks/investors")
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


@main.get("/bookmarks/investor")
@login_required
@check_user_info_complete
@check_verification
def get_investor_bookmark_ids():
    bookmarks_ids = InvestorBookmark.get_id_list(current_user.id)
    return jsonify({"bookmark_ids": bookmarks_ids})


@main.get("/investment-firm/<slug>")
def get_investment_firm(slug):
    unpaid = False

    if current_user.is_authenticated:
        user_payment = UserPayment.get_by_user_id(current_user.id)
        if current_user.is_admin:
            pass
        elif not user_payment:
            unpaid = True
        elif user_payment and not user_payment.is_active:
            unpaid = True
    else:
        unpaid = True

    investment_firm_model = InvestmentFirm.get_by_slug(slug)

    if not investment_firm_model:
        return jsonify({"status": "error", "message": "Investment Firm not found."}), 404
    if not investment_firm_model.is_public:
        return jsonify({"status": "error", "message": "Investment Firm is not public."}), 404

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

    if current_user.is_authenticated:
        is_bookmarked = InvestmentFirmBookmark.exists(investment_firm_model.id, current_user.id)
    else:
        is_bookmarked = False

    return jsonify({"investment_firm": investment_firm, "isBookmarked": is_bookmarked, "unpaid": unpaid})


@main.get("/investment-firm/investment/<int:firm_id>/get")
@login_required
@check_user_info_complete
@check_verification
def get_investment_firm_investment(firm_id):
    model_investments = Investment.get_by_investment_firm_id(firm_id)

    if not model_investments:
        return jsonify({"status": "error", "message": "Investments not found for this company."}), 404

    investments = []

    for model_investment in model_investments:
        company_investment = InvestmentSchema(
            id=model_investment.id,
            name=model_investment.funding_round.company.name if model_investment.funding_round.company else None,
            amount=model_investment.amount,
            round=model_investment.funding_round.round.name,
            announced_date=model_investment.funding_round.announced_date.strftime("%b %d, %Y")
            if model_investment.funding_round.announced_date
            else None,
        )
        investments.append(json.loads(company_investment.model_dump_json()))

    return jsonify({"investments": investments})


@main.get("/company/<slug>")
def get_company(slug):
    unpaid = False

    if current_user.is_authenticated:
        user_payment = UserPayment.get_by_user_id(current_user.id)
        if current_user.is_admin:
            pass
        elif not user_payment:
            unpaid = True
        elif user_payment and not user_payment.is_active:
            unpaid = True
    else:
        unpaid = True

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
        country=company_model.country.name if company_model.country else None,
        preferred_round={
            "id": company_model.preferred_round.id if company_model.preferred_round.id else None,
            "name": company_model.preferred_round.name if company_model.preferred_round.name else None,
        },
        industry={
            "id": company_model.industry.id if company_model.industry.id else None,
            "name": company_model.industry.name if company_model.industry.name else None,
        },
    ).model_dump()

    if current_user.is_authenticated:
        is_bookmarked = CompanyBookmark.exists(company_model.id, current_user.id)
    else:
        is_bookmarked = False

    return jsonify({"company": company, "isBookmarked": is_bookmarked, "unpaid": unpaid})


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


@main.get("/company/investment/<int:company_id>/get")
@login_required
@check_user_info_complete
@check_verification
def get_company_investment(company_id):
    model_investments = Investment.get_by_company_id(company_id)

    if not model_investments:
        return jsonify({"status": "error", "message": "Investments not found for this company."}), 404

    investments = []

    for model_investment in model_investments:
        if model_investment.investor:
            name = f"{model_investment.investor.first_name} {model_investment.investor.last_name}"
        elif model_investment.investment_firm:
            name = model_investment.investment_firm.name

        company_investment = InvestmentSchema(
            id=model_investment.id,
            name=name,
            amount=model_investment.amount,
            round=model_investment.funding_round.round.name,
            announced_date=model_investment.funding_round.announced_date.strftime("%b %d, %Y")
            if model_investment.funding_round.announced_date
            else None,
        )
        investments.append(json.loads(company_investment.model_dump_json()))
    return jsonify({"investments": investments})


@main.get("/bookmarks/company")
@login_required
@check_user_info_complete
@check_verification
def get_company_bookmark_ids():
    bookmarks_ids = CompanyBookmark.get_id_list(current_user.id)
    return jsonify({"bookmark_ids": bookmarks_ids})


@main.get("/bookmarks/companies")
@login_required
@check_user_info_complete
@check_verification
def get_company_bookmarks():
    user_id = current_user.id

    page = request.args.get("page", default=1, type=int)
    limit = 10
    offset = (page - 1) * limit

    companies = []
    bookmarks = CompanyBookmark.get_by_user_id(user_id, offset=offset, limit=limit)
    for db_company in bookmarks:
        if not isinstance(db_company, Company):
            return jsonify({"status": "error", "message": "Company not found."}), 404

        company = CompanyBookmarkSchema(
            id=db_company.id,
            name=db_company.name,
            about=db_company.description,
        )
        companies.append(json.loads(company.model_dump_json()))

    return jsonify({"bookmarks": companies})


@main.post("/investment-firm/<int:firm_id>/bookmark")
@login_required
@check_user_info_complete
@check_verification
def toggle_bookmark_investment_firm(firm_id):
    investment_firm = InvestmentFirm.get_by_id(int(firm_id))
    if not investment_firm or not investment_firm.is_public:
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


@main.route("/investment-firm/<slug>")
@login_required
@check_user_info_complete
@check_verification
def investment_firm_slug(slug):
    investment_firm = InvestmentFirm.get_by_slug(slug)
    if not investment_firm:
        return redirect(url_for("search.investor_search"))

    return render_template("investment_firm.html", investment_firm=investment_firm, user=current_user)


@main.get("/bookmarks/investment-firms")
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


@main.get("/bookmarks/investment-firm")
@login_required
@check_user_info_complete
@check_verification
def get_investment_firm_bookmark_ids():
    bookmarks_ids = InvestmentFirmBookmark.get_id_list(current_user.id)
    return jsonify({"bookmark_ids": bookmarks_ids})


@main.get("/notification/edit/<int:notification_id>")
@login_required
def update_notification(notification_id):
    notification = Notification.get_by_id(int(notification_id))
    if not notification:
        return redirect(url_for("search.investor_search"))

    if notification.user_id != current_user.id:
        return redirect(url_for("search.investor_search"))

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
    seven_days_ago = (datetime.now() - timedelta(days=7)).date().isoformat()

    for rule in current_app.url_map.iter_rules():
        if (
            rule.methods
            and "GET" in rule.methods
            and len(rule.arguments) == 0
            and not rule.rule.startswith("/admin")
            and not rule.rule.startswith("/onboarding")
            and not rule.rule.startswith("/login")
            and not rule.rule.startswith("/settings")
            and not rule.rule.startswith("/bookmark")
            and not rule.rule.startswith("/notification")
            and not rule.rule.startswith("/payment")
            and not rule.rule.startswith("/suggestion")
            and not rule.rule.startswith("/demo-search")
            and not rule.rule.startswith("/check-investor")
            and not rule.rule.startswith("/tier-selection")
            and not rule.rule.startswith("/logout")
            and not rule.rule.startswith("/health")
            and "email" not in rule.rule
            and "history" not in rule.rule
            and "oauth" not in rule.rule
        ):
            pages.append([rule.rule, seven_days_ago])

    root = ElementTree.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    for page in pages:
        url = ElementTree.SubElement(root, "url")
        loc = ElementTree.SubElement(url, "loc")
        loc.text = "https://globalify.xyz" + page[0]
        lastmod = ElementTree.SubElement(url, "lastmod")
        lastmod.text = page[1]
        changefreq = ElementTree.SubElement(url, "changefreq")
        changefreq.text = "weekly"
        priority = ElementTree.SubElement(url, "priority")
        priority.text = "0.5"

    sitemap_xml = ElementTree.tostring(root, encoding="utf-8")
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"

    return response


@main.route("/robots.txt")
def robots():
    robots_txt = """User-agent: *
Disallow: /admin
Disallow: /logout
Disallow: /onboarding
Disallow: /settings
Disallow: /login-linkedin
Disallow: /login-google
Disallow: /google-oauth
Disallow: /linkedin-oauth
Disallow: /payment

Sitemap: https://globalify.xyz/sitemap.xml"""
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
