import re

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required

from ..extensions import db
from ..models import EmailForNewsletter
from ..utils import Status, StatusType

main = Blueprint("main", __name__)


@main.get("/")
def index():
    return render_template("index_new.html")
    # return render_template("index.html")
    # return render_template("index_newsletter.html")


@main.route("/newsletter", methods=["POST"])
def newsletter():
    email = request.get_json().get("email")

    if not email:
        status = Status(StatusType.ERROR, "Please enter an email.")
        return jsonify(status.get_status())

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        status = Status(StatusType.ERROR, "Please enter a valid email.")
        return jsonify(status.get_status())

    email_for_newsletter = EmailForNewsletter.get_by_email(email)
    if email_for_newsletter:
        status = Status(StatusType.ERROR, "Email is already in the system.")
        return jsonify(status.get_status())

    email_for_newsletter = EmailForNewsletter(email=email)

    db.session.add(email_for_newsletter)
    db.session.commit()
    status = Status(StatusType.SUCCESS, "Email added.")
    return jsonify(status.get_status())


@main.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


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
    return render_template("errors/401.html"), 401


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
