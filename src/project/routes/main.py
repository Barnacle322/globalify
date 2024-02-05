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
from ..models import Company, Industry, InvestmentFirm, Investor, Round, Waitlist, WaitlistCharge
from ..utils.enums import Status, StatusType
from ..utils.errors.error_messages import NOT_AUTHORIZED
from ..utils.parse_medium import parse_medium_html
from ..utils.suggestion import weights


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


def construct_query_string(**kwargs):
    query_string = ""
    for key, value in kwargs.items():
        if isinstance(value, list):
            for item in value:
                query_string += f"&{key}={item}"
            continue
        if value:
            query_string += f"&{key}={value}"
    return query_string


@main.get("/")
def index():
    posts = parse_medium_html()
    return render_template("coming_soon.html", posts=posts)


@main.get("/waitlist")
def waitlist():
    return render_template("waitlist.html")


@main.get("/waitlist/apply")
def waitlist_apply():
    return render_template("waitlist/apply.html")


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


@main.route("/dashboard")
@main.route("/dashboard/investors")
@login_required
@check_user_info_complete
@check_verification
def dashboard():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    # ?q=Julie
    search_string = request.args.get("search", "")
    # ?page=1
    page = request.args.get("page", 1, type=int)
    # ?filter_field=firm_name
    filter_fields = request.args.getlist("filter_field")
    # ?sort_field=firm_name
    sort_field = request.args.get("sort_field", None)
    # ?descending= or ?descending=1
    descending = request.args.get("descending", False, type=bool)
    # ?min_investment=100000
    min_investment = request.args.get("min_investment", type=int)
    max_investment = request.args.get("max_investment", type=int)
    # ?rounds_exclusive= or ?rounds_exclusive=1
    rounds_exclusive = request.args.get("rounds_exclusive", False, type=bool)
    # ?industries_exclusive= or ?industries_exclusive=1
    industries_exclusive = request.args.get("industries_exclusive", False, type=bool)

    # ?round=Seed&round=Series+A
    rounds = []
    for round_name in request.args.getlist("round"):
        if round_object := Round.get_by_name(round_name):
            rounds.append(round_object)

    # ?industry=Healthcare&industry=FinTech
    industries = []
    for industry_name in request.args.getlist("industry"):
        if industry_object := Industry.get_by_name(industry_name):
            industries.append(industry_object)

    investors = Investor.get_pagination(
        page=page,
        search_string=search_string,
        filter_fields=filter_fields,
        rounds=rounds,
        industries=industries,
        sort_field=sort_field,
        descending=descending,
        min_investment=min_investment,
        max_investment=max_investment,
        rounds_exclusive=rounds_exclusive,
        industries_exclusive=industries_exclusive,
    )

    combined_query = construct_query_string(
        search=search_string,
        filter_field=[str(filter_field) for filter_field in filter_fields],
        sort_field=sort_field,
        descending=descending,
        rounds_exclusive=rounds_exclusive,
        industries_exclusive=industries_exclusive,
        round=[str(round_obj.name) for round_obj in rounds],
        industry=[str(industry.name) for industry in industries],
        min_investment=min_investment,
        max_investment=max_investment,
    )

    return render_template(
        "dashboard_investor.html",
        combined_query=combined_query,
        fields={
            "first_name": "First Name",
            "last_name": "Last Name",
            "firm_name": "Firm Name",
            "position": "Position",
            "about": "About",
            "n_investments": "Current Investments",
            "n_exits": "Successful Exits",
            "min_investment": "Minimum Investment",
            "max_investment": "Maximum Investment",
        },
        investors=investors,
        industry_list=Industry.get_all(),
        round_list=Round.get_all(),
        status_type=status_type,
        msg=msg,
    )


@main.route("/dashboard/suggestions")
@login_required
@check_user_info_complete
@check_verification
def get_suggestions():
    company = Company.get_by_user_id(current_user.id)

    investors = Investor.get_all()

    scored_investors = []

    for investor in investors:
        bias_score = investor.calculate_bias_score()
        location_score = investor.calculate_location_score(company)
        exits_score = investor.calculate_exits_score()
        industry_score = investor.calculate_industry_score(company)
        round_score = investor.calculate_round_score(company)
        completeness_score = investor.calculate_completeness_score()

        total_score = (
            weights["bias"] * bias_score
            + weights["location"] * location_score
            + weights["exits"] * exits_score
            + weights["industry"] * industry_score
            + weights["round"] * round_score
            + weights["completeness"] * completeness_score
        )
        scored_investors.append((investor, total_score))

    suggested_investors = sorted(
        (investor for investor in scored_investors),
        key=lambda investor: investor[1],
        reverse=True,
    )

    sorted_investors = [investor[0] for investor in suggested_investors][:15]

    return render_template(
        "suggestions.html",
        investors=sorted_investors,
    )


@main.route("/dashboard/investment-firms")
@login_required
@check_user_info_complete
@check_verification
def investment_firms():
    # ?q=Robinson-Sanders
    search_string = request.args.get("search", "")
    # ?page=1
    page = request.args.get("page", 1, type=int)
    # ?filter_field=name
    filter_fields = request.args.getlist("filter_field")
    # ?sort_field=name
    sort_field = request.args.get("sort_field", None)
    # ?descending= or ?descending=1
    descending = request.args.get("descending", False, type=bool)
    # ?min_investment=100000
    min_investment = request.args.get("min_investment", type=int)
    max_investment = request.args.get("max_investment", type=int)
    # ?rounds_exclusive= or ?rounds_exclusive=1
    rounds_exclusive = request.args.get("rounds_exclusive", False, type=bool)
    # ?industries_exclusive= or ?industries_exclusive=1
    industries_exclusive = request.args.get("industries_exclusive", False, type=bool)

    # ?round=Seed&round=Series+A
    rounds = []
    for round_name in request.args.getlist("round"):
        if round_object := Round.get_by_name(round_name):
            rounds.append(round_object)

    # ?industry=Healthcare&industry=FinTech
    industries = []
    for industry_name in request.args.getlist("industry"):
        if industry_object := Industry.get_by_name(industry_name):
            industries.append(industry_object)

    investment_firms = InvestmentFirm.get_pagination(
        page=page,
        search_string=search_string,
        filter_fields=filter_fields,
        rounds=rounds,
        industries=industries,
        sort_field=sort_field,
        descending=descending,
        min_investment=min_investment,
        max_investment=max_investment,
        rounds_exclusive=rounds_exclusive,
        industries_exclusive=industries_exclusive,
    )

    combined_query = construct_query_string(
        search=search_string,
        filter_field=[str(filter_field) for filter_field in filter_fields],
        sort_field=sort_field,
        descending=descending,
        rounds_exclusive=rounds_exclusive,
        industries_exclusive=industries_exclusive,
        round=[str(round.name) for round in rounds],
        industry=[str(industry.name) for industry in industries],
        min_investment=min_investment,
        max_investment=max_investment,
    )

    return render_template(
        "dashboard_firm.html",
        combined_query=combined_query,
        fields={
            "name": "Name",
            "about": "About",
            "n_investments": "Current Investments",
            "n_exits": "Successful Exits",
            "min_investment": "Minimum Investment",
            "max_investment": "Maximum Investment",
        },
        investment_firms=investment_firms,
        industry_list=Industry.get_all(),
        round_list=Round.get_all(),
    )


@main.route("/investor/<int:investor_id>")
@login_required
@check_user_info_complete
@check_verification
def investor(investor_id):
    investor = Investor.get_by_id(int(investor_id))
    if not investor:
        return redirect(url_for("main.dashboard"))

    return render_template("investor.html", investor=investor, user=current_user)


@main.route("/investment-firm/<int:firm_id>")
@login_required
@check_user_info_complete
@check_verification
def investment_firm(firm_id):
    investment_firm = InvestmentFirm.get_by_id(int(firm_id))
    if not investment_firm:
        return redirect(url_for("main.dashboard"))

    return render_template("investment_firm.html", investment_firm=investment_firm, user=current_user)


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
