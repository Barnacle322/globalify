import json
import re
from enum import Enum

import requests
from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db, login_manager, oauth
from ..models import (
    EmailForNewsletter,
    Industry,
    Round,
    User,
    Company,
    IndustrialGroup,
    Country,
)

main = Blueprint("main", __name__)


class StatusType(Enum):
    SUCCESS = 1
    WARNING = 2
    ERROR = 3


class Status:
    type: StatusType
    msg: str

    def __init__(self, type: StatusType, msg="An unknown error occurred."):
        self.type = type
        self.msg = msg

    def __repr__(self):
        return f"<{self.type} {self.msg}>"

    def get_status(self):
        return {"type": str(self.type), "msg": self.msg}


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


def oauth_user(email: str):
    user = User.get_by_email(email)
    if not user:
        user = User(email=email)
        db.session.add(user)
        db.session.commit()

    return user


@main.get("/")
def index():
    # return render_template("index.html")
    return render_template("index_newsletter.html")


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


@main.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not email or not password or not confirm_password:
            status = Status(StatusType.ERROR, "Please fill out all fields.")
            return render_template("register.html", status=status.get_status())

        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            status = Status(StatusType.ERROR, "Please enter a valid email.")
            return render_template("register.html", status=status.get_status())

        if password != confirm_password:
            status = Status(StatusType.ERROR, "Passwords do not match.")
            return render_template("register.html", status=status.get_status())

        signed_with_oauth = User.signed_with_oauth(email)
        if signed_with_oauth:
            status = Status(StatusType.WARNING, "Please sign in with Google.")
            return render_template("register.html", status=status.get_status())

        user = User.get_by_email(email)
        if user:
            status = Status(StatusType.ERROR, "Email is already in use.")
            return render_template("register.html", status=status.get_status())

        new_user = User(email=email)
        new_user.password = password

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for("main.login"))

    return render_template("register.html")


@main.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            status = Status(StatusType.ERROR, "Please fill out all fields.")
            return render_template("login.html", status=status.get_status())

        user = User.get_by_email(email)
        if not user:
            status = Status(StatusType.ERROR, "Email does not exist.")
            return render_template("login.html", status=status.get_status())

        if User.signed_with_oauth(email):
            status = Status(StatusType.WARNING, "Please sign in with Google.")
            return render_template("login.html", status=status.get_status())

        if not user.verify_password(password):
            status = Status(StatusType.ERROR, "Password is incorrect.")
            return render_template("login.html", status=status.get_status())

        login_user(user)
        return redirect(url_for("main.index"))

    return render_template("login.html")


@main.route("/login-google")
def google_login():
    return oauth.globalify.authorize_redirect(
        redirect_uri=url_for("main.google_callback", _external=True)
    )


@main.route("/google-oauth")
def google_callback():
    authorization = oauth.globalify.authorize_access_token()
    if authorization:
        user_info = authorization.get("userinfo")
        if user_info:
            email = user_info.get("email")

            user = oauth_user(email)

            first_name = user_info.get("given_name")
            last_name = user_info.get("family_name")
            picture = user_info.get("picture")

            user.first_name = first_name
            user.last_name = last_name
            user.picture = picture
            db.session.commit()
            login_user(user)

    return redirect(url_for("main.index"))


@main.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("main.index"))


@main.route("/terms-of-service")
def terms_of_service():
    return render_template("terms_of_service.html")


@main.route("/privacy-policy")
def privacy_policy():
    return render_template("privacy_policy.html")


@main.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@main.errorhandler(401)
def unauthorized(e):
    return render_template("401.html"), 401


@main.route("/test")
def test():
    db.session.rollback()
    country = db.session.query(Country).filter_by(code="KG").first()
    new_industrial_group = IndustrialGroup.query.filter_by(name="Agriculture").first()
    new_industrial_group2 = IndustrialGroup.query.filter_by(name="Automotive").first()
    new_industry = Industry.query.filter_by(name="Manufacturing").first()
    new_round = Round.query.filter_by(name="Seed").first()
    new_company = Company(
        name="test",
        description="test",
        number_of_employees=1,
        country=country,
        website="test",
        picture="test",
        preferred_round=new_round,
        industrial_group=[new_industrial_group, new_industrial_group2],
        industry=[new_industry],
    )
    db.session.add(new_company)
    db.session.commit()
    return "Hello world"


@main.route("/test2")
def test2():
    company = Company.query.filter_by(name="test").first()
    # return jsonify(company.country.code)
    print(company.industry)
    return jsonify(list(map(lambda x: x.name, company.industry)))
