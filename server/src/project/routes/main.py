import xml.etree.ElementTree as ElementTree
from datetime import datetime, timedelta
from functools import wraps

from flask import Blueprint, current_app, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..models import InvestmentFirm, Investor, User
from ..utils.errors.auth_error_messages import NOT_AUTHORIZED
from ..utils.google_storage import load_pfp
from ..utils.status_enum import Status, StatusType

main = Blueprint("main", __name__)


def check_user_info_complete(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:  # type: ignore
            return redirect(url_for("auth.login"))
        elif not current_user.user_info[0].is_complete:  # type: ignore
            return redirect(url_for("auth.onboarding"))
        return func(*args, **kwargs)

    return decorated_function


def check_verification(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:  # type: ignore
            return redirect(url_for("auth.login"))
        # TODO
        elif not current_user.is_verified:  # type: ignore
            # return redirect(url_for("auth.verify"))
            pass
        return func(*args, **kwargs)

    return decorated_function


@main.get("/")
def index():
    return render_template("coming_soon.html")


@main.get("/waitlist")
def waitlist():
    return render_template("waitlist.html")


@main.route("/dashboard")
@main.route("/dashboard/investors")
@login_required
@check_user_info_complete
@check_verification
def dashboard():
    authenticated_user: User = current_user  # type: ignore
    if authenticated_user.is_anonymous:
        return redirect(url_for("auth.login"))

    pfp_base64 = load_pfp(authenticated_user.user_info[0].pfp_uuid)  # type: ignore

    search_query = request.args.get("q", "")
    page_num = request.args.get("page", 1, type=int)
    investors = Investor.get_pagination(page=page_num, query=search_query)

    if page_num > investors.pages and investors.pages > 0:  # type: ignore
        return redirect(url_for("main.search", search=search_query, pagenum=1))

    return render_template(
        "dashboard_investor.html",
        pfp_base64=pfp_base64,
        search_query=search_query,
        investors=investors,
    )


@main.route("/dashboard/investment-firms")
@login_required
@check_user_info_complete
@check_verification
def investment_firms():
    authenticated_user: User = current_user  # type: ignore
    if authenticated_user.is_anonymous:
        return redirect(url_for("auth.login"))

    pfp_base64 = load_pfp(authenticated_user.user_info[0].pfp_uuid)  # type: ignore

    search_query = request.args.get("q", "")
    page_num = request.args.get("page", 1, type=int)
    investment_firms = InvestmentFirm.get_pagination(page=page_num, query=search_query)

    if page_num > investment_firms.pages and investment_firms.pages > 0:  # type: ignore
        return redirect(url_for("main.search", search=search_query, pagenum=1))

    return render_template(
        "dashboard_firm.html",
        pfp_base64=pfp_base64,
        search_query=search_query,
        investment_firms=investment_firms,
    )


@main.route("/investor/<int:investor_id>")
@login_required
@check_user_info_complete
@check_verification
def investor(investor_id):
    investor = Investor.get_by_id(int(investor_id))
    if not investor:
        return redirect(url_for("main.dashboard"))

    return render_template("investor.html", investor=investor)


@main.route("/investment-firm/<int:firm_id>")
@login_required
@check_user_info_complete
@check_verification
def investment_firm(firm_id):
    investment_firm = InvestmentFirm.get_by_id(int(firm_id))
    if not investment_firm:
        return redirect(url_for("main.dashboard"))

    return render_template("investment_firm.html", investment_firm=investment_firm)


@main.route("/pricing")
def pricing():
    return render_template("pricing.html")


@main.route("/about")
def about():
    return render_template("about.html")


@main.route("/docs")
@main.route("/jobs")
@main.route("/partners")
@main.route("/help")
@main.route("/claim")
@main.route("/investor-database")
@main.route("/startup-database")
@main.route("/digest")
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
    robots_txt = "User-agent: *\nDisallow: /admin\nDisallow: /logout\nDisallow: /onboarding\nDisallow: /company-form\nDisallow: /login-linkedin\nDisallow: /login-google\nDisallow: /google-oauth\nDisallow: /linkedin-oauth\n\nSitemap: https://globalify.xyz/sitemap.xml"
    response = make_response(robots_txt)
    response.headers["Content-Type"] = "text/plain"
    return response


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
