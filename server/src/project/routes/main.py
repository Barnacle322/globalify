import base64
from datetime import datetime, timedelta

from flask import Blueprint, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..models import Investor, UserInfo

# from ..extensions import db
from ..utils.google_storage import download_blob_into_memory
from ..utils.status_enum import Status, StatusType

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return render_template("index.html")


@main.route("/dashboard")
@login_required
def dashboard():
    authenticated_user = UserInfo.get_by_user_id(current_user.id)  # type: ignore
    if not authenticated_user:
        status = Status(StatusType.ERROR, "You are not logged in").get_status()
        return redirect(url_for("payment.index", **status))  # type: ignore

    pfp_base64 = False
    try:
        if pfp_uuid := authenticated_user.pfp_uuid:
            pfp = download_blob_into_memory(pfp_uuid)  # type: ignore
            pfp_base64 = base64.b64encode(pfp).decode("utf-8")
    except Exception as e:
        print(e)

    search_query = request.args.get("q", "")
    page_num = request.args.get("page", 1, type=int)
    investors = Investor.get_pagination(page=page_num, query=search_query)

    if page_num > investors.pages and investors.pages > 0:  # type: ignore
        return redirect(url_for("main.search", search=search_query, pagenum=1))

    return render_template(
        "dashboard.html",
        pfp_base64=pfp_base64,
        search_query=search_query,
        investors=investors,
    )


@main.route("/investor/<int:investor_id>")
def investor(investor_id):
    investor = Investor.get_by_id(investor_id)
    if not investor:
        return redirect(url_for("main.search"))

    return render_template("investor.html", investor=investor)


@main.route("/terms-of-service")
def terms_of_service():
    return render_template("terms_of_service.html")


@main.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html")


@main.errorhandler(400)
def bad_request(e):
    return render_template("errors/400.html"), 400


@main.errorhandler(401)
def unauthorized(e):
    next_url = str(request.path)
    return redirect(url_for("auth.login", next=next_url))


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
