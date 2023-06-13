from flask import Blueprint, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from ..extensions import db, login_manager

from ..models import User

main = Blueprint("main", __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@main.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")

@main.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@main.errorhandler(401)
def unauthorized(e):
    return render_template("401.html"), 401
