from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, fresh_login_required, login_required, logout_user

from ..extensions import db
from ..models import Company, Country, Industry, Round, User, UserInfo, UserPayment
from ..utils.enums import Status, StatusType, Tier
from .main import check_user_info_complete, check_verification
from .payment import get_invoices

settings = Blueprint("settings", __name__)


@settings.route("/")
@settings.route("/general")
@login_required
@check_user_info_complete
@check_verification
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    return render_template(
        "settings/general.html",
        user=authenticated_user,
        status_type=status_type,
        msg=msg,
    )


@settings.route("/security")
@login_required
@check_user_info_complete
@check_verification
def security():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template(
        "settings/security.html",
        status_type=status_type,
        msg=msg,
    )


@settings.route("/plan")
@login_required
@check_user_info_complete
@check_verification
def plan():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_payment = UserPayment.get_by_user_id(authenticated_user.id)
    subscription = {"tier": Tier.FREE}
    if user_payment and user_payment.customer_id and user_payment.subscription_id:
        subscription = user_payment.sanitize()

    return render_template(
        "settings/plan.html",
        subscription=subscription,
    )


@settings.route("/billing")
@login_required
@check_user_info_complete
@check_verification
def billing():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    invoices = get_invoices(authenticated_user)

    return render_template(
        "settings/billing.html",
        user=authenticated_user,
        invoices=invoices,
    )


@settings.post("/personal-info")
@login_required
@check_user_info_complete
@check_verification
@fresh_login_required
def change_personal_info():  # noqa
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    first_name = request.form.get("first-name")
    last_name = request.form.get("last-name")
    username = request.form.get("username")
    bio = request.form.get("bio")

    user_info = authenticated_user.user_info[0]  # type: ignore
    if first_name and first_name.strip() != user_info.first_name:
        if first_name == " ":
            status = Status(StatusType.ERROR, "First name cannot be empty.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.first_name = first_name.strip()

    if last_name and last_name.strip() != user_info.last_name:
        if last_name == " ":
            status = Status(StatusType.ERROR, "Last name cannot be empty.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.last_name = last_name.strip()

    if bio and bio.strip() != user_info.bio:
        if bio == " ":
            status = Status(StatusType.ERROR, "Bio cannot be empty.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.bio = bio.strip()

    if username and username.strip() != user_info.username:
        if username == " ":
            status = Status(StatusType.ERROR, "Username cannot be empty.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        if UserInfo.is_taken(username):
            status = Status(StatusType.ERROR, "Username is taken.").get_status()
            return redirect(url_for("settings.index", _external=False, **status))

        user_info.username = username.strip()

    db.session.commit()

    status = Status(StatusType.SUCCESS, "Personal info successfully changed.").get_status()
    return redirect(url_for("settings.index", _external=False, **status))


@settings.route("/delete-account", methods=["GET", "POST"])
@login_required
@check_user_info_complete
@check_verification
@fresh_login_required
def delete_account():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    if request.method == "POST":
        # NOTE: Decorators hold db session open
        # so we need to close it here to properly delete the user objects
        db.session.close()
        db.session.begin()

        # Access the user_info attribute to add it to the session
        _ = authenticated_user.user_info  # type: ignore

        db.session.delete(authenticated_user)
        db.session.commit()
        logout_user()

        return redirect(url_for("main.index", _external=False))

    return render_template("settings/delete_oauth_account.html")


@settings.route("/company", methods=["GET", "POST"])
@login_required
def change_company_info():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    company = Company.get_by_user_id(authenticated_user.id)
    if not company:
        abort(404)

    industries = Industry.get_all()
    rounds = Round.get_all()
    countries = Country.get_all()

    if request.method == "POST":
        company_name = request.form.get("company-name", "")
        if company_name and company_name.strip() != company.name:
            if company_name == " ":
                status = Status(StatusType.ERROR, "Company name cannot be empty.").get_status()
                return redirect(url_for("settings.change_company_info", _external=False, **status))
            company.name = company_name.strip()

        preferred_round_id = request.form.get("round", type=int)
        industry_id = request.form.get("industry", type=int)

        if not preferred_round_id or not industry_id:
            status = Status(StatusType.ERROR, "Please select rounds and industries.").get_status()
            return redirect(
                url_for(
                    "settings.change_company_info",
                    _external=False,
                    **status,
                )
            )

        country_id = request.form.get("country", type=int)
        if not country_id:
            status = Status(StatusType.ERROR, "Country ID is required.").get_status()
            return redirect(url_for("settings.change_company_info", _external=False, **status))

        company.description = request.form.get("description", "").strip()
        company.number_of_employees = request.form.get("number_of_employees", 0, type=int)
        company.country_id = country_id
        company.preferred_round_id = preferred_round_id
        company.industry_id = industry_id
        company.website = request.form.get("website", "")
        company.coordinates = Country.get_by_id(country_id).name  # type: ignore
        db.session.commit()

        status = Status(StatusType.SUCCESS, "Company successfully changed.").get_status()
        return redirect(
            url_for(
                "settings.change_company_info",
                _external=False,
                **status,
            )
        )

    return render_template(
        "settings/company.html",
        industries=industries,
        rounds=rounds,
        countries=countries,
        company=company,
        status_type=status_type,
        msg=msg,
    )
