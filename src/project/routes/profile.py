import re
from datetime import datetime

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


@profile.route("/", methods=["GET", "POST"])
def user_profile():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_id = authenticated_user.id

    user = User.get_by_id(user_id)
    if not user:
        status = Status(StatusType.ERROR, "User does not exist.").get_status()
        return redirect(url_for("profile.user_profile", _external=False, **status))

    user_info = UserInfo.get_by_user_id(user_id)
    if not user_info:
        status = Status(StatusType.ERROR, "User info does not exist.").get_status()
        return redirect(url_for("profile.user_profile", _external=False, **status))

    user_payment = UserPayment.get_by_user_id(user_id)
    if not user_payment:
        status = Status(StatusType.ERROR, "User payment does not exist.").get_status()
        return redirect(url_for("profile.user_profile", _external=False, **status))

    if request.method == "POST":
        email = request.form.get("email")
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        username = request.form.get("username", "").strip()
        tier = request.form.get("tier")

        if not email or not first_name or not last_name or not username or not tier:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(url_for("profile.user_profile", _external=False, **status))

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            status = Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status()
            return redirect(url_for("profile.user_profile", _external=False, **status))

        if (existing_user := User.get_by_email(email)) and existing_user.id != user_id:
            status = Status(StatusType.ERROR, AUTH_EMAIL_USED).get_status()
            return redirect(url_for("profile.user_profile", _external=False, **status))

        if UserInfo.is_taken(username) and user_info.username != username:
            status = Status(StatusType.ERROR, "Username already exists.").get_status()
            return redirect(url_for("profile.user_profile", _external=False, **status))

        if pfp_uuid := upload_pfp(request.files["pfp"]):
            user_info.pfp_uuid = pfp_uuid

        try:
            user_info.linkedin = request.form.get("linkedin")
            user_info.instagram = request.form.get("instagram")
            user_info.twitter = request.form.get("twitter")
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("profile.user_profile", _external=False, **status))

        user.email = email
        user_info.first_name = first_name
        user_info.last_name = last_name
        user_info.username = username
        user_info.bio = request.form.get("bio", "").strip()
        user_info.language = request.form.get("language", "English")

        user_payment.customer_id = request.form.get("customer_id", "")
        user_payment.subscription_id = request.form.get("subscription_id", "")

        user_payment.created = (
            datetime.strptime(created_str + ":00", "%Y-%m-%dT%H:%M:%S")
            if (created_str := request.form.get("created")) and len(created_str) == 16
            else datetime.strptime(created_str, "%Y-%m-%dT%H:%M:%S")
            if created_str
            else None
        )

        user_payment.expires_at = (
            datetime.strptime(expires_at + ":00", "%Y-%m-%dT%H:%M:%S")
            if (expires_at := request.form.get("expires_at")) and len(expires_at) == 16
            else datetime.strptime(expires_at, "%Y-%m-%dT%H:%M:%S")
            if expires_at
            else None
        )

        tier = request.form.get("tier", "elevate")
        if tier not in ["elevate", "connect pro", "boost academy", "free"]:
            status = Status(StatusType.ERROR, "Invalid tier").get_status()
            return redirect(url_for("profile.user_profile", _external=False, **status))
        user_payment.tier = Tier(tier)

        db.session.commit()
        return redirect(url_for("profile.user_profile"))

    return render_template(
        "profile/user_profile.html",
        user=authenticated_user,
        user_info=user_info,
        user_payment=user_payment,
        languages=language_list,
        status_type=status_type,
        msg=msg,
        Tier=Tier,
    )


@profile.route("/company", methods=["GET", "POST"])
def company_profile():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    company = Company.get_by_user_id(authenticated_user.id)
    if not company:
        abort(404)

    industries = Industry.get_all()
    rounds = Round.get_all()
    countries = Country.get_all()

    if request.method == "POST":
        name = request.form.get("company-name", "").strip()

        preferred_round_id = request.form.get("round", type=int)
        industry_id = request.form.get("industry", type=int)

        if not industry_id:
            status = Status(StatusType.ERROR, "Industry ID is required.").get_status()
            return redirect(url_for("profile.company_profile", _external=False, **status))

        if not preferred_round_id or not industry_id:
            status = Status(StatusType.ERROR, "Please select rounds and industries.").get_status()
            return redirect(
                url_for(
                    "profile.company_profile",
                    _external=False,
                    **status,
                )
            )

        country_id = request.form.get("country", type=int)
        if not country_id:
            status = Status(StatusType.ERROR, "Country ID is required.").get_status()
            return redirect(url_for("profile.company_profile", _external=False, **status))

        company.name = name
        company.description = request.form.get("description", "").strip()
        company.number_of_employees = request.form.get("number_of_employees", 0, type=int)
        company.country_id = country_id
        company.preferred_round_id = preferred_round_id
        company.industry_id = industry_id
        company.website = request.form.get("website", "")

        if pfp := request.files["pfp"]:
            try:
                resized_pfp = prepare_picture(pfp)
                pfp_uuid = upload_blob(resized_pfp.read())
                company.pfp_uuid = str(pfp_uuid)
            except Exception as e:
                print(f"An error occurred: {e}")

        db.session.commit()
        return redirect(url_for("profile.company_profile"))

    return render_template(
        "profile/company_profile.html",
        industries=industries,
        rounds=rounds,
        countries=countries,
        company=company,
        status_type=status_type,
        msg=msg,
    )
