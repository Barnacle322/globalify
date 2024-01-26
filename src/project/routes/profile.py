import re

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, fresh_login_required, login_required, logout_user

from src.project.models.helpers import Country, Industry, Round
from src.project.models.user import Company

from ..extensions import db
from ..models import User, UserInfo, UserOauth, UserPayment, UserRegular
from ..utils.errors.auth_error_messages import AUTH_EMAIL_USED, AUTH_FIELDS_INCOMPLETE, AUTH_INVALID_EMAIL
from ..utils.google_storage import load_pfp, prepare_picture, upload_blob, upload_pfp
from ..utils.info_lists import languages as language_list
from ..utils.status_enum import Status, StatusType, Tier
from .main import check_user_info_complete, check_verification

profile = Blueprint("profile", __name__)


@profile.route("/me", methods=["GET"])
def user_profile():

    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user = User.get_by_id(authenticated_user.id)
    user_info = UserInfo.get_by_user_id(authenticated_user.id)

    if user:
        return render_template("profile/user_profile.html", user=user, user_info=user_info)
    else:
        abort(404)
