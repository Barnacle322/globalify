from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, fresh_login_required, login_required, logout_user

from ..extensions import db
from ..models import (
    Company,
    Country,
    Industry,
    Investor,
    InvestorBackup,
    InvestorPointOrigin,
    NotableInvestment,
    Round,
    User,
    UserInfo,
    UserPayment,
)
from ..schemas.investor import IndustrySchema, InvestorPointOriginSchema, NotableInvestmentSchema, RoundSchema
from ..utils.enums import Status, StatusType, Tier
from ..utils.google_helpers.google_storage import delete_blob_from_url, upload_picture
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
    return render_template(
        "settings/security.html",
    )


@settings.route("/plan")
@login_required
@check_user_info_complete
@check_verification
def plan():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_payment = UserPayment.get_by_user_id(authenticated_user.id)
    if user_payment and user_payment.customer_id and user_payment.subscription_id:
        subscription = user_payment.sanitize()
    else:
        subscription = {
            "tier": Tier.FREE,
            "is_active": False,
            "start_date": None,
            "end_date": None,
        }
    return render_template(
        "settings/plan.html",
        subscription=subscription,
        status_type=status_type,
        msg=msg,
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


def add_https_prefix(url):
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    return url


@settings.post("/personal-info")
@login_required
@check_user_info_complete
@check_verification
def change_personal_info():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    first_name = request.form.get("first-name")
    email_public = request.form.get("email_public")
    linkedin_public = request.form.get("linkedin_public")
    instagram_public = request.form.get("instagram_public")
    twitter_public = request.form.get("twitter_public")
    last_name = request.form.get("last-name")
    username = request.form.get("username")
    bio = request.form.get("bio")
    linkedin_url = request.form.get("linkedin")
    instagram_url = request.form.get("instagram")
    twitter_url = request.form.get("twitter")
    picture = request.files.get("picture")

    user_info = authenticated_user.user_info  # type: ignore

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

    if picture:
        try:
            picture_url = upload_picture(picture)
            if user_info.picture_url:
                try:
                    delete_blob_from_url(user_info.picture_url)
                except Exception as e:
                    print(e)
            user_info.picture_url = picture_url
        except Exception as e:
            print(e)
            status = Status(StatusType.ERROR, "Error loading image. Please reach out to our support team!").get_status()
            return redirect(url_for("settings.index", _external=False, **status))

    if linkedin_url:
        linkedin_url = add_https_prefix(linkedin_url)
        try:
            user_info.linkedin_url = linkedin_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
    else:
        user_info.linkedin_url = None

    if instagram_url:
        instagram_url = add_https_prefix(instagram_url)
        try:
            user_info.instagram_url = instagram_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
    else:
        user_info.instagram_url = None

    if twitter_url:
        twitter_url = add_https_prefix(twitter_url)
        try:
            user_info.twitter_url = twitter_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
    else:
        user_info.twitter_url = None

    user_info.email_public = bool(email_public)
    user_info.linkedin_public = bool(linkedin_public)
    user_info.instagram_public = bool(instagram_public)
    user_info.twitter_public = bool(twitter_public)

    db.session.commit()

    status = Status(StatusType.SUCCESS, "Personal info successfully changed.").get_status()
    return redirect(url_for("settings.index", _external=False, **status))


@settings.route("/delete-account", methods=["GET", "POST"])
@login_required
@check_user_info_complete
@check_verification
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
@check_user_info_complete
@check_verification
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

        picture = request.files.get("picture")

        if picture:
            try:
                picture_url = upload_picture(picture)
                if company.picture_url:
                    try:
                        delete_blob_from_url(company.picture_url)
                    except Exception as e:
                        print(e)
                company.picture_url = picture_url
            except Exception as e:
                print(e)
                status = Status(
                    StatusType.ERROR, "Error loading image. Please reach out to our support team!"
                ).get_status()
                return redirect(url_for("settings.index", _external=False, **status))

        country_id = request.form.get("country", type=int)
        if not country_id:
            status = Status(StatusType.ERROR, "Country ID is required.").get_status()
            return redirect(url_for("settings.change_company_info", _external=False, **status))

        website_url = request.form.get("website", "")
        if website_url:
            website_url = add_https_prefix(website_url)
            try:
                company.website_url = website_url
            except Exception as e:
                status = Status(StatusType.ERROR, str(e)).get_status()
                return redirect(url_for("settings.change_company_info", _external=False, **status))
        else:
            company.website_url = None

        company.description = request.form.get("description", "").strip()
        company.number_of_employees = request.form.get("number_of_employees", 0, type=int)
        company.country_id = country_id
        company.preferred_round_id = preferred_round_id
        company.industry_id = industry_id
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


@settings.get("/investor")
@login_required
@check_user_info_complete
@check_verification
def edit_investor_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investor = Investor.get_by_user_id(current_user.id)
    if not investor:
        status = Status(StatusType.ERROR, "You don't have claimed investor profile yet.").get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    if investor.user_id != current_user.id:
        status = Status(StatusType.ERROR, "Not authorized.").get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    notable_investments = NotableInvestment.get_all()
    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "settings/investor.html",
        investor=investor,
        rounds=rounds,
        industries=industries,
        notable_investments=notable_investments,
        status_type=status_type,
        msg=msg,
    )


@settings.post("/investor")
@login_required
@check_user_info_complete
@check_verification
def edit_investor():
    investor = Investor.get_by_user_id(current_user.id)
    if not investor:
        return jsonify({"status": "error", "message": "Investor not found."}, 404)

    if investor.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Not authorized."}, 401)

    form_data = request.get_json()

    first_name = form_data.get("first_name")
    last_name = form_data.get("last_name") or None
    firm_name = form_data.get("firm_name") or None
    position = form_data.get("position") or None
    about = form_data.get("about") or None
    location = form_data.get("location") or None

    n_investments = form_data.get("n_investments") or 0
    n_exits = form_data.get("n_exits") or 0
    min_investment = form_data.get("min_investment") or 0
    max_investment = form_data.get("max_investment") or 0
    selected_round_ids = form_data.get("rounds") or []
    selected_industry_ids = form_data.get("industries") or []
    selected_notable_investment_ids = form_data.get("notable_investments") or []

    website = form_data.get("website") or None
    linkedin = form_data.get("linkedin") or None
    twitter = form_data.get("twitter") or None
    email = form_data.get("email") or None
    phone_number = form_data.get("phone_number") or None

    selected_rounds = list(Round.get_by_id_list(selected_round_ids))
    selected_industries = list(Industry.get_by_id_list(selected_industry_ids))
    selected_notable_investments = list(NotableInvestment.get_by_id_list(selected_notable_investment_ids))

    existing_email = User.get_by_email(email) if email else None
    if existing_email and existing_email.id != investor.user_id:
        status = Status(StatusType.ERROR, "Email already exists").get_status()
        return redirect(url_for("settings.edit_investor_view", _external=True, **status))

    if not first_name:
        status = Status(StatusType.ERROR, "First name shouldn't be empty").get_status()
        return redirect(url_for("settings.edit_investor_view", _external=True, **status))

    investor.first_name = first_name
    investor.last_name = last_name
    investor.set_slug()
    investor.firm_name = firm_name
    investor.position = position
    investor.about = about
    investor.website = website
    investor.linkedin = linkedin
    investor.twitter = twitter
    investor.email = email
    investor.phone_number = phone_number
    investor.n_investments = n_investments
    investor.n_exits = n_exits
    investor.min_investment = min_investment
    investor.max_investment = max_investment
    investor.location = location
    investor.rounds = selected_rounds
    investor.industries = selected_industries
    investor.notable_investments = selected_notable_investments

    investor_backup = InvestorBackup.get_by_investor_id(investor.id)
    if investor_backup:
        investor_backup.first_name = first_name
        investor_backup.last_name = last_name
        investor_backup.slug = investor.slug
        investor_backup.firm_name = firm_name
        investor_backup.position = position
        investor_backup.about = about
        investor_backup.website = website
        investor_backup.linkedin = linkedin
        investor_backup.twitter = twitter
        investor_backup.email = email
        investor_backup.phone_number = phone_number
        investor_backup.n_investments = n_investments
        investor_backup.n_exits = n_exits
        investor_backup.min_investment = min_investment
        investor_backup.max_investment = max_investment
        investor_backup.location = location
        investor_backup.rounds = selected_rounds
        investor_backup.industries = selected_industries
        investor_backup.notable_investments = selected_notable_investments
        db.session.add(investor_backup)

    db.session.commit()

    investor.upsert_data()

    status = Status(StatusType.SUCCESS, "Investor updated.").get_status()

    return redirect(url_for("settings.edit_investor_view", _external=False, **status))


@settings.get("/investor/point-origin")
@login_required
@check_user_info_complete
@check_verification
def investor_point_origin_data():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    investor = Investor.get_by_user_id(authenticated_user.id)
    if not investor:
        status = Status(StatusType.ERROR, "You don't have claimed investor profile yet.").get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    investor_point_origin = InvestorPointOrigin.get_by_investor_id(investor.id)
    if not investor_point_origin:
        status = Status(StatusType.ERROR, "No backup data found.").get_status()
        return redirect(url_for("settings.edit_investor_view", _external=True, **status))

    data = InvestorPointOriginSchema(
        first_name=investor_point_origin.first_name,
        last_name=investor_point_origin.last_name,
        slug=investor_point_origin.slug,
        firm_name=investor_point_origin.firm_name,
        position=investor_point_origin.position,
        about=investor_point_origin.about,
        website=investor_point_origin.website,
        linkedin=investor_point_origin.linkedin,
        twitter=investor_point_origin.twitter,
        email=investor_point_origin.email,
        phone_number=investor_point_origin.phone_number,
        n_investments=investor_point_origin.n_investments,
        n_exits=investor_point_origin.n_exits,
        min_investment=investor_point_origin.min_investment,
        max_investment=investor_point_origin.max_investment,
        location=investor_point_origin.location,
        notable_investments=[
            NotableInvestmentSchema(title=ni.name) for ni in investor_point_origin.notable_investments
        ],
        rounds=[RoundSchema(title=r.name) for r in investor_point_origin.rounds],
        industries=[IndustrySchema(title=i.name) for i in investor_point_origin.industries],
    )

    return data.model_dump()


@settings.get("/investor/restore")
@login_required
@check_user_info_complete
@check_verification
def restore_investor_data():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    investor = Investor.get_by_user_id(authenticated_user.id)
    if not investor:
        status = Status(StatusType.ERROR, "You don't have claimed investor profile yet.").get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    investor_point_origin = InvestorPointOrigin.get_by_investor_id(investor.id)
    if investor_point_origin:
        investor.first_name = investor_point_origin.first_name
        investor.last_name = investor_point_origin.last_name
        investor.slug = investor_point_origin.slug
        investor.firm_name = investor_point_origin.firm_name
        investor.position = investor_point_origin.position
        investor.about = investor_point_origin.about
        investor.website = investor_point_origin.website
        investor.linkedin = investor_point_origin.linkedin
        investor.twitter = investor_point_origin.twitter
        investor.email = investor_point_origin.email
        investor.phone_number = investor_point_origin.phone_number
        investor.n_investments = investor_point_origin.n_investments
        investor.n_exits = investor_point_origin.n_exits
        investor.min_investment = investor_point_origin.min_investment
        investor.max_investment = investor_point_origin.max_investment
        investor.location = investor_point_origin.location
        investor.rounds = investor_point_origin.rounds
        investor.industries = investor_point_origin.industries
        investor.notable_investments = investor_point_origin.notable_investments

        db.session.commit()

        investor.upsert_data()
    else:
        status = Status(StatusType.ERROR, "No backup data found.").get_status()
        return redirect(url_for("settings.edit_investor_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor data restored.").get_status()
    return redirect(url_for("settings.edit_investor_view", _external=False, **status))
