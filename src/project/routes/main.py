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
    InvestmentFirm,
    Investor,
    Notification,
    User,
    UserInfo,
    UserPayment,
    entity_search,
)
from ..models.entity import EntityBookmark
from ..schemas.investor import (
    InvestmentFirmSchema,
    InvestorSchema,
)
from ..utils.decorators import check_user_info_complete, check_verification
from ..utils.enums import EntityType, Status, StatusType
from ..utils.errors.error_messages import (
    NOT_AUTHORIZED,
)
from ..utils.posthog import capture_profile_view

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return render_template("index.html")


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

    description = ""
    if investor.about:
        description = investor.about[:140]
        if not description.endswith("."):
            description += "."

    if investor.firm_name:
        if investor.position:
            description += f" {investor.full_name} is also a {investor.position} in {investor.firm_name}."
        else:
            description += f" {investor.full_name} is also working with {investor.firm_name}."

    if investor.location:
        description += f" Located in {investor.location}."

    twitter_slug = f"@{investor.twitter.split('/')[-1]}" if investor.twitter else None
    picture_url = (
        f"https://unavatar.io/twitter/{investor.twitter.split('/')[-1]}"
        if investor.twitter
        else "https://globalify.xyz/static/elements/metapreview.png"
    )

    return render_template(
        "investor.html",
        investor=investor,
        description=description,
        picture_url=picture_url,
        twitter_slug=twitter_slug,
        current_user=current_user if current_user.is_authenticated else None,
        status_type=status_type,
        msg=msg,
    )


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
        # Phase 1b: check EntityBookmark (PERSON) instead of InvestorBookmark.
        is_bookmarked = EntityBookmark.exists(current_user.id, EntityType.PERSON, investor.id)
    else:
        is_bookmarked = False

    capture_profile_view(
        profile_type="investor",
        properties={
            "slug": slug,
            "unpaid": unpaid,
        },
    )

    return jsonify({"investor": investor.model_dump(), "unpaid": unpaid, "isBookmarked": is_bookmarked})


@main.get("/check-investor")
@login_required
def check_investor():
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    user_info = UserInfo.get_by_user_id(current_user.id)
    if not user_info:
        return jsonify({"status": "error", "message": "User Info not found."}), 404

    try:
        result = entity_search.get_search(
            query=user_info.full_name,
            entity_type="person",
            per_page=18,
        )
    except Exception:
        result = {"hits": []}

    existing_investors = [
        {"id": hit.get("document", {}).get("db_id"), "name": hit.get("document", {}).get("name")}
        for hit in result.get("hits", [])
    ]
    return jsonify({"existing_investors": existing_investors})


@main.post("/investor/<int:investor_id>/bookmark")
@login_required
@check_user_info_complete
@check_verification
def toggle_bookmark_investor(investor_id):
    investor = Investor.get_by_id(int(investor_id))
    if not investor or not investor.is_public:
        return jsonify({"status": "error", "message": "Investor not found."}), 404

    # Phase 1b: use EntityBookmark (PERSON entity type) instead of InvestorBookmark.
    if EntityBookmark.exists(current_user.id, EntityType.PERSON, investor.id):
        existing = db.session.scalar(
            db.select(EntityBookmark).where(
                EntityBookmark.user_id == current_user.id,
                EntityBookmark.entity_type == EntityType.PERSON,
                EntityBookmark.entity_id == investor.id,
            )
        )
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"bookmarked": False}, 200)

    new_bookmark = EntityBookmark(user_id=current_user.id, entity_type=EntityType.PERSON, entity_id=investor.id)
    db.session.add(new_bookmark)
    db.session.commit()

    return jsonify({"bookmarked": True}, 200)


@main.get("/bookmarks/investors")
@login_required
@check_user_info_complete
@check_verification
def get_investor_bookmarks():
    # Phase 1b: return EntityBookmark records for PERSON entities.
    # NOTE(phase-2): when the frontend is rebuilt this response shape will be
    # updated to serve Person/Organization data directly.
    user_id = current_user.id

    bookmarks = EntityBookmark.get_by_user_id(user_id)
    person_bookmarks = [bm for bm in bookmarks if bm.entity_type == EntityType.PERSON]

    result = [
        {"entity_type": bm.entity_type, "entity_id": bm.entity_id, "created_at": str(bm.created_at)}
        for bm in person_bookmarks
    ]
    return jsonify({"bookmarks": result})


@main.get("/bookmarks/investor")
@login_required
@check_user_info_complete
@check_verification
def get_investor_bookmark_ids():
    # Phase 1b: return entity_ids for PERSON bookmarks via EntityBookmark.
    bookmarks = EntityBookmark.get_by_user_id(current_user.id)
    bookmark_ids = [bm.entity_id for bm in bookmarks if bm.entity_type == EntityType.PERSON]
    return jsonify({"bookmark_ids": bookmark_ids})


@main.get("/investment-firm/<slug>/get")
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
        # Phase 1b: check EntityBookmark (ORG) instead of InvestmentFirmBookmark.
        is_bookmarked = EntityBookmark.exists(current_user.id, EntityType.ORG, investment_firm_model.id)
    else:
        is_bookmarked = False

    capture_profile_view(
        profile_type="investment_firm",
        properties={
            "slug": slug,
            "unpaid": unpaid,
        },
    )

    return jsonify({"investment_firm": investment_firm, "isBookmarked": is_bookmarked, "unpaid": unpaid})


@main.post("/investment-firm/<int:firm_id>/bookmark")
@login_required
@check_user_info_complete
@check_verification
def toggle_bookmark_investment_firm(firm_id):
    investment_firm = InvestmentFirm.get_by_id(int(firm_id))
    if not investment_firm or not investment_firm.is_public:
        return jsonify({"status": "error", "message": "Investment Firm not found."}), 404

    # Phase 1b: use EntityBookmark (ORG entity type) instead of InvestmentFirmBookmark.
    if EntityBookmark.exists(current_user.id, EntityType.ORG, investment_firm.id):
        existing = db.session.scalar(
            db.select(EntityBookmark).where(
                EntityBookmark.user_id == current_user.id,
                EntityBookmark.entity_type == EntityType.ORG,
                EntityBookmark.entity_id == investment_firm.id,
            )
        )
        db.session.delete(existing)
        db.session.commit()
        return jsonify({"bookmarked": False}, 200)

    new_bookmark = EntityBookmark(user_id=current_user.id, entity_type=EntityType.ORG, entity_id=investment_firm.id)
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

    description = ""
    if investment_firm.about:
        description = investment_firm.about[:140]
        if not description.endswith("."):
            description += "."

    if investment_firm.notable_investments:
        investments_list = ", ".join(investment.name for investment in investment_firm.notable_investments)
        description += f" {investment_firm.name} has notable investments in companies such as: {investments_list}."

    if investment_firm.industries:
        industries_list = ", ".join(industry.name for industry in investment_firm.industries)
        description += f" Works with {industries_list}."

    if investment_firm.rounds:
        rounds_list = ", ".join(investment_round.name for investment_round in investment_firm.rounds)
        description += f" Prefered rounds: {rounds_list}."

    if investment_firm.location:
        description += f" Located in {investment_firm.location}."

    twitter_slug = f"@{investment_firm.twitter.split('/')[-1]}" if investment_firm.twitter else None

    picture_url = (
        f"https://unavatar.io/twitter/{investment_firm.twitter.split('/')[-1]}"
        if investment_firm.twitter
        else "https://globalify.xyz/static/elements/metapreview.png"
    )

    return render_template(
        "investment_firm.html",
        description=description,
        picture_url=picture_url,
        twitter_slug=twitter_slug,
        investment_firm=investment_firm,
        current_user=current_user if current_user.is_authenticated else None,
    )


@main.get("/bookmarks/investment-firms")
@login_required
@check_user_info_complete
@check_verification
def get_investment_firms_bookmarks():
    # Phase 1b: return EntityBookmark records for ORG entities.
    # NOTE(phase-2): when the frontend is rebuilt this response shape will be
    # updated to serve Organization data directly.
    user_id = current_user.id

    bookmarks = EntityBookmark.get_by_user_id(user_id)
    org_bookmarks = [bm for bm in bookmarks if bm.entity_type == EntityType.ORG]

    result = [
        {"entity_type": bm.entity_type, "entity_id": bm.entity_id, "created_at": str(bm.created_at)}
        for bm in org_bookmarks
    ]
    return jsonify({"bookmarks": result})


@main.get("/bookmarks/investment-firm")
@login_required
@check_user_info_complete
@check_verification
def get_investment_firm_bookmark_ids():
    # Phase 1b: return entity_ids for ORG bookmarks via EntityBookmark.
    bookmarks = EntityBookmark.get_by_user_id(current_user.id)
    bookmark_ids = [bm.entity_id for bm in bookmarks if bm.entity_type == EntityType.ORG]
    return jsonify({"bookmark_ids": bookmark_ids})


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
