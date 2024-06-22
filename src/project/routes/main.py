import json
import re
import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

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
    UserPayment,
    Waitlist,
    WaitlistCharge,
)
from ..schemas.investor import InvestmentFirmBookmarkSchema, InvestorBookmarkSchema
from ..utils.enums import NotificationDestination, Status, StatusType
from ..utils.errors.error_messages import NOT_AUTHORIZED
from ..utils.parse_medium import parse_medium_html
from ..utils.suggestion import WEIGHTS, check_weights

main = Blueprint("main", __name__)


def check_user_info_complete(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:  # type: ignore
            return redirect(url_for("auth.login"))
        elif not current_user.user_info.is_complete:  # type: ignore
            return redirect(url_for("auth.onboarding"))
        return func(*args, **kwargs)

    return decorated_function


def check_verification(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:  # type: ignore
            return redirect(url_for("auth.login"))
        elif not current_user.is_verified:  # type: ignore
            return redirect(url_for("auth.email_verification_required"))
        return func(*args, **kwargs)

    return decorated_function


def generate_pagination(current_page: int, total_pages: int, around_count: int = 2) -> dict:
    """
    Generate a pagination dictionary.

    Args:
        current_page (int): The current page number.
        total_pages (int): The total number of pages.
        around_count (int, optional): The number of pages to show around the current page. Defaults to 4.

    Returns:
        dict: A dictionary with keys 'current_page', 'prev', 'next', and 'pages'.
    """
    # Calculate all the page ranges
    start_pages = range(1, min(3, total_pages + 1))
    around_pages = range(max(1, current_page - around_count), min(current_page + around_count + 1, total_pages + 1))
    end_pages = range(max(current_page + around_count + 1, total_pages - 1), total_pages + 1)

    # Build the pages list
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


@main.get("/incubation")
def incubation():
    return render_template("incubation.html")


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


@main.route("/suggestions")
@login_required
@check_user_info_complete
@check_verification
def get_suggestions():
    access = True
    user_payment = UserPayment.get_by_user_id(current_user.id)
    if current_user.is_admin:
        access = True
    elif not user_payment:
        access = False
    elif user_payment and not user_payment.is_active:
        access = False

    company = Company.get_by_user_id(current_user.id)

    bookmarks = InvestorBookmark.get_id_list(current_user.id)

    check_weights(WEIGHTS)
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
    access = True
    user_payment = UserPayment.get_by_user_id(current_user.id)
    if current_user.is_admin:
        access = True
    elif not user_payment:
        access = False
    elif user_payment and not user_payment.is_active:
        access = False

    company = Company.get_by_user_id(current_user.id)

    bookmarks = InvestmentFirmBookmark.get_id_list(current_user.id)

    check_weights(WEIGHTS)
    suggested_investment_firms = InvestmentFirm.get_suggestions(company=company, quantity=15)

    return render_template(
        "suggestions_investment_firms.html",
        investment_firms=suggested_investment_firms,
        access=access,
        bookmark_ids=bookmarks,
    )


@main.route("/search/investment-firms", methods=["GET", "POST"])
@login_required
@check_user_info_complete
@check_verification
def search_investment_firms():
    notifications = Notification.get_unread(
        current_user.id,
        NotificationDestination.SEARCH,
        is_read=False,
    )

    search_string = request.args.get("search", "")
    sort_by = request.args.get("sort_field", "db_id")
    sort_desc = request.args.get("descending", False, type=bool)
    min_investment = request.args.get("min_investment", type=int)
    max_investment = request.args.get("max_investment", type=int)
    page = request.args.get("page", 1, type=int)

    rounds_exclusive = request.args.get("rounds_exclusive", False, type=bool)
    rounds = []
    for round_name in request.args.getlist("round"):
        if round_object := Round.get_by_name(round_name):
            rounds.append(round_object.name)

    industries_exclusive = request.args.get("industries_exclusive", False, type=bool)
    industries = []
    for industry_name in request.args.getlist("industry"):
        if industry_object := Industry.get_by_name(industry_name):
            industries.append(industry_object.name)

    countries = []
    for country_name in request.args.getlist("country"):
        if country_object := Country.get_by_name(country_name):
            countries.append(country_object.name)

    query_by = [
        "location",
        "country",
        "rounds",
        "industries",
        "embedding",
        "notable_investments",
        "name",
    ]

    result = InvestmentFirm.get_search(
        query_string=search_string,
        query_by=query_by,
        sort_by=sort_by,
        sort_desc=sort_desc,
        rounds=rounds,
        industries=industries,
        rounds_exclusive=rounds_exclusive,
        industries_exclusive=industries_exclusive,
        min_investment=min_investment,
        max_investment=max_investment,
        page=page,
        per_page=9,
        countries=countries,
    )
    investment_firms = result.get("investment_firms")

    bookmarks = InvestmentFirmBookmark.get_id_list(current_user.id)

    user_payment = UserPayment.get_by_user_id(current_user.id)
    unpaid = False
    if current_user.is_admin:
        pass
    elif not user_payment and page > 1:
        unpaid = True
    elif user_payment and not user_payment.is_active and page > 1:
        unpaid = True

    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    fields = {
        "n_investments": "Number of Investments",
        "n_exits": "Number of Exits",
        "min_investment": "Minimum Investment",
        "max_investment": "Maximum Investment",
        "n_employees": "Number of Employees",
    }

    return render_template(
        "search_investment_firms.html",
        investment_firms=investment_firms,
        query=search_string,
        fields=fields,
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        notifications=notifications,
        industry_list=Industry.get_all(),
        round_list=Round.get_all(),
        countries=Country.get_all(),
        unpaid=unpaid,
        bookmark_ids=bookmarks,
    )


@main.route("/search", methods=["GET", "POST"])
@login_required
@check_user_info_complete
@check_verification
def search():
    notifications = Notification.get_unread(
        current_user.id,
        NotificationDestination.SEARCH,
        is_read=False,
    )

    search_string = request.args.get("search", "")
    sort_by = request.args.get("sort_field", "db_id")
    sort_desc = request.args.get("descending", False, type=bool)
    min_investment = request.args.get("min_investment", type=int)
    max_investment = request.args.get("max_investment", type=int)
    page = request.args.get("page", 1, type=int)

    rounds_exclusive = request.args.get("rounds_exclusive", False, type=bool)
    rounds = []
    for round_name in request.args.getlist("round"):
        if round_object := Round.get_by_name(round_name):
            rounds.append(round_object.name)

    industries_exclusive = request.args.get("industries_exclusive", False, type=bool)
    industries = []
    for industry_name in request.args.getlist("industry"):
        if industry_object := Industry.get_by_name(industry_name):
            industries.append(industry_object.name)

    countries = []
    for country_name in request.args.getlist("country"):
        if country_object := Country.get_by_name(country_name):
            countries.append(country_object.name)

    query_by = [
        "location",
        "country",
        "rounds",
        "industries",
        "embedding",
        "notable_investments",
        "name",
        "firm_name",
        "position",
    ]

    result = Investor.get_search(
        query_string=search_string,
        query_by=query_by,
        sort_by=sort_by,
        sort_desc=sort_desc,
        rounds=rounds,
        industries=industries,
        rounds_exclusive=rounds_exclusive,
        industries_exclusive=industries_exclusive,
        min_investment=min_investment,
        max_investment=max_investment,
        page=page,
        per_page=9,
        countries=countries,
    )
    investors = result.get("investors")

    bookmarks = InvestorBookmark.get_id_list(current_user.id)

    user_payment = UserPayment.get_by_user_id(current_user.id)
    unpaid = False
    if current_user.is_admin:
        pass
    elif not user_payment and page > 1:
        unpaid = True
    elif user_payment and not user_payment.is_active and page > 1:
        unpaid = True

    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    fields = {
        "n_investments": "Number of Investments",
        "n_exits": "Number of Exits",
        "min_investment": "Minimum Investment",
        "max_investment": "Maximum Investment",
    }

    return render_template(
        "search.html",
        investors=investors,
        query=search_string,
        fields=fields,
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        notifications=notifications,
        industry_list=Industry.get_all(),
        round_list=Round.get_all(),
        countries=Country.get_all(),
        unpaid=unpaid,
        user=current_user,
        bookmark_ids=bookmarks,
    )


@main.get("/demo_search")
def demo_search():
    search_query = request.args.get("search", "")
    result = Investor.get_search(
        query_string=search_query,
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
    investors = result.get("investors")

    return jsonify(investors)


@main.route("/investor/<slug>")
@login_required
@check_user_info_complete
@check_verification
def investor_slug(slug):
    investor = Investor.get_by_slug(slug)
    if not investor:
        return redirect(url_for("main.search"))

    return render_template("investor.html", investor=investor, user=current_user)


@main.post("/investor/<int:investor_id>/bookmark")
@login_required
@check_user_info_complete
@check_verification
def toggle_bookmark_investor(investor_id):
    investor = Investor.get_by_id(int(investor_id))
    if not investor:
        return jsonify({"status": "error", "message": "Investor not found."}, 404)

    bookmark = InvestorBookmark.get_by_id(investor.id, current_user.id)

    if bookmark:
        db.session.delete(bookmark)
        db.session.commit()
        return jsonify({"bookmarked": False}, 200)

    new_bookmark = InvestorBookmark(investor_id=investor.id, user_id=current_user.id)

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

    bookmarks = InvestorBookmark.get_by_user_id(user_id, offset=offset, limit=limit)

    investors = []
    for db_investor in bookmarks:
        if not isinstance(db_investor, Investor):
            return jsonify({"status": "error", "message": "Investors not found."}, 404)

        investor = InvestorBookmarkSchema(
            id=db_investor.id,
            name=db_investor.first_name + " " + db_investor.last_name,
            position=db_investor.position,
            firm_name=db_investor.firm_name,
            about=db_investor.about,
            twitter=db_investor.twitter,
            slug=db_investor.slug,
        )
        investors.append(json.loads(investor.model_dump_json()))

    return jsonify({"bookmarks": investors})


@main.get("/investment-firms/bookmarks")
@login_required
@check_user_info_complete
@check_verification
def get_investment_firms_bookmarks():
    user_id = current_user.id

    page = request.args.get("page", default=1, type=int)
    limit = 10
    offset = (page - 1) * limit

    bookmarks = InvestmentFirmBookmark.get_by_user_id(user_id, offset=offset, limit=limit)

    investment_firms = []

    for db_investment_firm in bookmarks:
        if not isinstance(db_investment_firm, InvestmentFirm):
            return jsonify({"status": "error", "message": "Investment Firms not found."}, 404)

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
        return jsonify({"status": "error", "message": "Investment Firm not found."}, 404)

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

    return jsonify({"status": "success"}, 200)


@main.post("/waitlist-email")
def waitlist_email():
    email = request.get_json().get("email")

    if not email:
        status = Status(StatusType.ERROR, "Please enter an email.").get_status()
        return jsonify(**status)

    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        status = Status(StatusType.ERROR, "Please enter a valid email.").get_status()
        return jsonify(**status)

    email_for_newsletter = Waitlist.get_by_email(email)
    if email_for_newsletter:
        status = Status(StatusType.ERROR, "Email is already in the system.").get_status()
        return jsonify(**status)

    new_waitlist = Waitlist(email=email)
    db.session.add(new_waitlist)
    db.session.commit()

    status = Status(StatusType.SUCCESS, "Email added.").get_status()
    return jsonify(**status)


@main.get("/waitlist/cancel")
def cancel_waitlist():
    return render_template("waitlist/cancel.html")


@main.get("/waitlist/success")
def success_waitlist():
    return render_template("waitlist/success.html")


@main.get("/download/<key>")
def download(key):
    waitlist_charge = WaitlistCharge.get_by_random_key(key)

    if not waitlist_charge:
        return render_template("download.html", can_download=False)

    if waitlist_charge.downloaded:
        return render_template("download.html", can_download=False)

    return render_template("download.html", can_download=True, random_key=key)


@main.post("/download")
def post_download():
    random_key = request.form.get("random_key", "")
    waitlist_charge = WaitlistCharge.get_by_random_key(random_key)

    if not waitlist_charge or waitlist_charge.downloaded:
        return redirect(url_for("main.index"))

    waitlist_charge.downloaded = True
    db.session.commit()

    return send_from_directory(
        "static", "elements/download/Globalify_Early_Bird_Investor_List.xlsx", as_attachment=True
    )


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


@main.route("/sitemap.xml")
def sitemap():
    pages = []
    ten_days_ago = (datetime.now() - timedelta(days=10)).date().isoformat()  # type: ignore

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
