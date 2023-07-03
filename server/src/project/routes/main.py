import re
from enum import Enum

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

from ..extensions import db, login_manager
from ..models import User

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


@main.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


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

        if not user.verify_password(password):
            status = Status(StatusType.ERROR, "Password is incorrect.")
            return render_template("login.html", status=status.get_status())

        login_user(user)
        return redirect(url_for("main.index"))

    return render_template("login.html")


@main.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@main.errorhandler(401)
def unauthorized(e):
    return render_template("401.html"), 401
