import re
from datetime import datetime
from functools import wraps

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user

from src.project.utils.google_storage import prepare_picture, upload_blob, upload_pfp

from ..extensions import db
from ..models import (
    Company,
    Country,
    Industry,
    InvestmentFirm,
    Investor,
    Round,
    User,
    UserInfo,
    UserPayment,
)
from ..utils.errors.auth_error_messages import (
    AUTH_EMAIL_USED,
    AUTH_FIELDS_INCOMPLETE,
    AUTH_INVALID_EMAIL,
)
from ..utils.info_lists import languages as language_list
from ..utils.status_enum import Status, StatusType, Tier

admin = Blueprint("admin", __name__)


def is_admin(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if current_user.is_authenticated and current_user.is_admin:
            return func(*args, **kwargs)
        else:
            return render_template("errors/403.html"), 403

    return decorated_view


def construct_query_string(**kwargs):
    query_string = ""
    for key, value in kwargs.items():
        if isinstance(value, list):
            for item in value:
                query_string += f"&{key}={item}"
            continue
        if value:
            query_string += f"&{key}={value}"
    return query_string


@admin.get("/")
@is_admin
def index():
    # ?q=Julie
    search_string = request.args.get("search", "")
    # ?page=1
    page = request.args.get("page", 1, type=int)
    # ?filter_field=firm_name
    filter_fields = request.args.getlist("filter_field")
    # ?sort_field=firm_name
    sort_field = request.args.get("sort_field", None)
    # ?descending= or ?descending=1
    descending = request.args.get("descending", False, type=bool)
    # ?min_investment=100000
    min_investment = request.args.get("min_investment", type=int)
    max_investment = request.args.get("max_investment", type=int)
    # ?rounds_exclusive= or ?rounds_exclusive=1
    rounds_exclusive = request.args.get("rounds_exclusive", False, type=bool)
    # ?industries_exclusive= or ?industries_exclusive=1
    industries_exclusive = request.args.get("industries_exclusive", False, type=bool)

    # ?round=Seed&round=Series+A
    rounds = []
    for round_name in request.args.getlist("round"):
        if round_object := Round.get_by_name(round_name):
            rounds.append(round_object)

    # ?industry=Healthcare&industry=FinTech
    industries = []
    for industry_name in request.args.getlist("industry"):
        if industry_object := Industry.get_by_name(industry_name):
            industries.append(industry_object)

    investors = Investor.get_pagination(
        page=page,
        search_string=search_string,
        filter_fields=filter_fields,
        rounds=rounds,
        industries=industries,
        sort_field=sort_field,
        descending=descending,
        min_investment=min_investment,
        max_investment=max_investment,
        rounds_exclusive=rounds_exclusive,
        industries_exclusive=industries_exclusive,
    )

    combined_query = construct_query_string(
        search=search_string,
        filter_field=[str(filter_field) for filter_field in filter_fields],
        sort_field=sort_field,
        descending=descending,
        rounds_exclusive=rounds_exclusive,
        industries_exclusive=industries_exclusive,
        round=[str(round_obj.name) for round_obj in rounds],
        industry=[str(industry.name) for industry in industries],
        min_investment=min_investment,
        max_investment=max_investment,
    )

    return render_template(
        "admin/index.html",
        combined_query=combined_query,
        fields={
            "first_name": "First Name",
            "last_name": "Last Name",
            "firm_name": "Firm Name",
            "position": "Position",
            "about": "About",
            "n_investments": "Current Investments",
            "n_exits": "Successful Exits",
            "min_investment": "Minimal Investment",
            "max_investment": "Maximal Investment",
        },
        investors=investors,
        industries=Industry.get_all(),
        rounds=Round.get_all(),
    )


def validate_field(
    value,
    error_message,
    redirect_url=None,
    user_id=None,
    investment_firm_id=None,
    investor_id=None,
    company_id=None,
):
    if not value.strip():
        status = Status(StatusType.ERROR, error_message).get_status()
        if redirect_url:
            return redirect(
                url_for(
                    redirect_url,
                    _external=False,
                    user_id=user_id,
                    investment_firm_id=investment_firm_id,
                    investor_id=investor_id,
                    company_id=company_id,
                    **status,
                )
            )
        return status
    return None


@admin.get("/investors/")
@is_admin
def get_all_investors():
    investors = Investor.get_all()
    return render_template("admin/investors.html", investors=investors)


@admin.route("/investor/add", methods=["GET", "POST"])
@is_admin
def add_investor():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        if error := validate_field(first_name, "First name", "First name cannot be empty.", "admin.add_investor"):
            return error

        if error := validate_field(last_name, "Last name", "Last name cannot be empty.", "admin.add_investor"):
            return error

        email = request.form.get("email")
        if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return redirect(
                url_for(
                    "admin.add_investor", _external=False, **Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status()
                )
            )

        existing_investor = Investor.get_by_email(email=email)  # type: ignore
        if existing_investor:
            status = Status(StatusType.ERROR, AUTH_EMAIL_USED).get_status()
            return redirect(
                url_for(
                    "admin.add_investor",
                    _external=False,
                    **status,
                )
            )

        selected_round_ids = request.form.getlist("selected_rounds")
        selected_industry_ids = request.form.getlist("selected_industries")

        if not selected_round_ids or not selected_industry_ids:
            status = Status(StatusType.ERROR, "Please select rounds and industries.").get_status()
            return redirect(
                url_for(
                    "admin.add_investor",
                    _external=False,
                    **status,
                )
            )

        n_investments = request.form.get("n_investments", 0, type=int)
        n_exits = request.form.get("n_exits", 0, type=int)
        min_investment = request.form.get("min_investment", 0, type=int)
        max_investment = request.form.get("max_investment", 0, type=int)

        selected_rounds = [Round.get_by_id(int(rid)) for rid in selected_round_ids if rid.isdigit()]
        selected_industries = [Industry.get_by_id(int(iid)) for iid in selected_industry_ids if iid.isdigit()]

        new_investor = Investor(
            first_name=first_name,
            last_name=last_name,
            firm_name=request.form.get("firm_name", "").strip(),
            about=request.form.get("about", "").strip(),
            position=request.form.get("position", "").strip(),
            website=request.form.get("website"),
            linkedin=request.form.get("linkedin"),
            twitter=request.form.get("twitter"),
            email=email,
            phone_number=request.form.get("phone_number"),
            location=request.form.get("location", "").strip(),
            n_investments=n_investments,
            n_exits=n_exits,
            min_investment=min_investment,
            max_investment=max_investment,
            rounds=selected_rounds,
            industries=selected_industries,
        )

        db.session.add(new_investor)
        db.session.commit()

        return redirect(url_for("admin.index"))

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/add_investor.html", rounds=rounds, industries=industries, status_type=status_type, msg=msg
    )


@admin.route("/investor/edit/<int:investor_id>", methods=["GET", "POST"])
@is_admin
def edit_investor(investor_id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investor = Investor.get_by_id(investor_id)
    if not investor:
        abort(404)

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()

        error = validate_field(
            first_name, "First name", "First name cannot be empty.", "admin.edit_investor", investor_id=investor_id
        )
        if error:
            return error

        error = validate_field(
            last_name, "Last name", "Last name cannot be empty.", "admin.edit_investor", investor_id=investor_id
        )
        if error:
            return error

        email = request.form.get("email", "")
        if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            status = Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status()
            return redirect(
                url_for(
                    "admin.edit_investor",
                    _external=False,
                    investor_id=investor_id,
                    **status,
                )
            )

        existing_investor = Investor.query.filter(Investor.email == email, Investor.id != investor_id).first()
        if existing_investor:
            status = Status(StatusType.ERROR, "Email already exists.").get_status()
            return redirect(
                url_for(
                    "admin.edit_investor",
                    _external=False,
                    investor_id=investor_id,
                    **status,
                )
            )

        selected_round_ids = request.form.getlist("selected_rounds")
        selected_industry_ids = request.form.getlist("selected_industries")

        if not selected_round_ids or not selected_industry_ids:
            status = Status(StatusType.ERROR, "Please select rounds and industries.").get_status()
            return redirect(
                url_for(
                    "admin.edit_investor",
                    _external=False,
                    investor_id=investor_id,
                    **status,
                )
            )

        investor.first_name = first_name
        investor.last_name = last_name
        investor.firm_name = request.form.get("firm_name", "").strip()
        investor.about = request.form.get("about", "").strip()
        investor.position = request.form.get("position", "").strip()
        investor.website = request.form.get("website", "")
        investor.linkedin = request.form.get("linkedin", "")
        investor.twitter = request.form.get("twitter", "")
        investor.email = email
        investor.phone_number = request.form.get("phone_number", "")
        investor.n_investments = request.form.get("n_investments", 0, type=int)
        investor.n_exits = request.form.get("n_exits", 0, type=int)
        investor.min_investment = request.form.get("min_investment", 0, type=int)
        investor.max_investment = request.form.get("max_investment", 0, type=int)
        investor.location = request.form.get("location", "").strip()
        investor.rounds = list(Round.get_by_id_list(selected_round_ids))
        investor.industries = list(Industry.get_by_id_list(selected_industry_ids))

        db.session.commit()

        return redirect(url_for("admin.index"))

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/edit_investor.html",
        investor=investor,
        rounds=rounds,
        industries=industries,
        status_type=status_type,
        msg=msg,
    )


@admin.route("/investor/delete/<int:investor_id>", methods=["POST"])
@is_admin
def delete_investor(investor_id):
    investor = Investor.get_by_id(investor_id)
    if not investor:
        abort(404)

    db.session.delete(investor)
    db.session.commit()

    return redirect(url_for("admin.index"))


@admin.get("/investment-firms/")
@is_admin
def get_all_investment_firms():
    # ?q=Robinson-Sanders
    search_string = request.args.get("search", "")
    # ?page=1
    page = request.args.get("page", 1, type=int)
    # ?filter_field=name
    filter_fields = request.args.getlist("filter_field")
    # ?sort_field=name
    sort_field = request.args.get("sort_field", None)
    # ?descending= or ?descending=1
    descending = request.args.get("descending", False, type=bool)
    # ?min_investment=100000
    min_investment = request.args.get("min_investment", type=int)
    max_investment = request.args.get("max_investment", type=int)
    # ?rounds_exclusive= or ?rounds_exclusive=1
    rounds_exclusive = request.args.get("rounds_exclusive", False, type=bool)
    # ?industries_exclusive= or ?industries_exclusive=1
    industries_exclusive = request.args.get("industries_exclusive", False, type=bool)

    # ?round=Seed&round=Series+A
    rounds = []
    for round_name in request.args.getlist("round"):
        if round_object := Round.get_by_name(round_name):
            rounds.append(round_object)

    # ?industry=Healthcare&industry=FinTech
    industries = []
    for industry_name in request.args.getlist("industry"):
        if industry_object := Industry.get_by_name(industry_name):
            industries.append(industry_object)

    investment_firms = InvestmentFirm.get_pagination(
        page=page,
        search_string=search_string,
        filter_fields=filter_fields,
        rounds=rounds,
        industries=industries,
        sort_field=sort_field,
        descending=descending,
        min_investment=min_investment,
        max_investment=max_investment,
        rounds_exclusive=rounds_exclusive,
        industries_exclusive=industries_exclusive,
    )

    combined_query = construct_query_string(
        search=search_string,
        filter_field=[str(filter_field) for filter_field in filter_fields],
        sort_field=sort_field,
        descending=descending,
        rounds_exclusive=rounds_exclusive,
        industries_exclusive=industries_exclusive,
        round=[str(round.name) for round in rounds],
        industry=[str(industry.name) for industry in industries],
        min_investment=min_investment,
        max_investment=max_investment,
    )

    return render_template(
        "admin/get_investment_firms.html",
        combined_query=combined_query,
        fields={
            "name": "Name",
            "about": "About",
            "n_investments": "Current Investments",
            "n_exits": "Successful Exits",
            "min_investment": "Minimum Investment",
            "max_investment": "Maximum Investment",
        },
        investment_firms=investment_firms,
        industries=Industry.get_all(),
        rounds=Round.get_all(),
    )


@admin.route("/investment-firm/add", methods=["GET", "POST"])
@is_admin
def add_investment_firm():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if request.method == "POST":
        name = request.form.get("name", "").strip()

        error = validate_field(name, "Name", "Name cannot be empty.", "admin.add_investment_firm")
        if error:
            return error

        email = request.form.get("email", "")
        if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            status = Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status()
            return redirect(
                url_for(
                    "admin.add_investment_firm",
                    _external=False,
                    **status,
                )
            )

        existing_investor = InvestmentFirm.get_by_email(email=email)
        if existing_investor:
            status = Status(StatusType.ERROR, "Email already exists.").get_status()
            return redirect(
                url_for(
                    "admin.add_investment_firm",
                    _external=False,
                    **status,
                )
            )

        selected_round_ids = request.form.getlist("selected_rounds")
        selected_industry_ids = request.form.getlist("selected_industries")

        if not selected_round_ids or not selected_industry_ids:
            status = Status(StatusType.ERROR, "Please select rounds and industries.").get_status()
            return redirect(
                url_for(
                    "admin.add_investment_firm",
                    _external=False,
                    **status,
                )
            )

        selected_rounds = [Round.get_by_id(int(rid)) for rid in selected_round_ids if rid.isdigit()]
        selected_industries = [Industry.get_by_id(int(iid)) for iid in selected_industry_ids if iid.isdigit()]

        new_investor = InvestmentFirm(
            name=name,
            about=request.form.get("about", "").strip(),
            website=request.form.get("website"),
            email=email,
            phone_number=request.form.get("phone_number"),
            n_investments=request.form.get("n_investments", 0, type=int),
            n_exits=request.form.get("n_exits", 0, type=int),
            n_employees=request.form.get("n_employees", 0, type=int),
            min_investment=request.form.get("min_investment", 0, type=int),
            max_investment=request.form.get("max_investment", 0, type=int),
            rounds=selected_rounds,
            industries=selected_industries,
        )

        db.session.add(new_investor)
        db.session.commit()

        return redirect(url_for("admin.get_all_investment_firms"))

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/add_investment_firm.html", rounds=rounds, industries=industries, status_type=status_type, msg=msg
    )


@admin.route("/investment-firm/edit/<int:investment_firm_id>", methods=["GET", "POST"])
@is_admin
def edit_investment_firm(investment_firm_id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investment_firm = InvestmentFirm.get_by_id(investment_firm_id)
    if not investment_firm:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        error = validate_field(
            name, "Name", "Name cannot be empty.", "admin.edit_investment_firm", investment_firm_id=investment_firm_id
        )
        if error:
            return error

        email = request.form.get("email", "")
        if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            status = Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status()
            return redirect(
                url_for(
                    "admin.edit_investment_firm",
                    _external=False,
                    investment_firm_id=investment_firm_id,
                    **status,
                )
            )

        existing_investor = InvestmentFirm.query.filter(
            InvestmentFirm.email == email, InvestmentFirm.id != investment_firm_id
        ).first()
        if existing_investor:
            status = Status(StatusType.ERROR, "Email already exists.").get_status()
            return redirect(
                url_for(
                    "admin.edit_investment_firm",
                    _external=False,
                    investment_firm_id=investment_firm_id,
                    **status,
                )
            )

        selected_round_ids = request.form.getlist("selected_rounds")
        selected_industry_ids = request.form.getlist("selected_industries")

        if not selected_round_ids or not selected_industry_ids:
            status = Status(StatusType.ERROR, "Please select rounds and industries.").get_status()
            return redirect(
                url_for(
                    "admin.edit_investment_firm",
                    _external=False,
                    investment_firm_id=investment_firm_id,
                    **status,
                )
            )

        selected_rounds = [Round.get_by_id(int(round_id)) for round_id in selected_round_ids if round_id.isdigit()]
        selected_industries = [
            Industry.get_by_id(int(industry_id)) for industry_id in selected_industry_ids if industry_id.isdigit()
        ]

        investment_firm.name = name
        investment_firm.about = request.form.get("about", "").strip()
        investment_firm.website = request.form.get("website", "")
        investment_firm.email = email
        investment_firm.phone_number = request.form.get("phone_number", "")
        investment_firm.n_investments = request.form.get("n_investments", 0, type=int)
        investment_firm.n_exits = request.form.get("n_exits", 0, type=int)
        investment_firm.n_employees = request.form.get("n_employees", 0, type=int)
        investment_firm.min_investment = request.form.get("min_investment", 0, type=int)
        investment_firm.max_investment = request.form.get("max_investment", 0, type=int)

        investment_firm.rounds = selected_rounds  # type: ignore
        investment_firm.industries = selected_industries  # type: ignore

        db.session.commit()

        return redirect(url_for("admin.get_all_investment_firms"))

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/edit_investment_firm.html",
        investment_firm=investment_firm,
        rounds=rounds,
        industries=industries,
        status_type=status_type,
        msg=msg,
    )


@admin.route("/investment-firm/delete/<int:investment_firm_id>", methods=["POST"])
@is_admin
def delete_investment_firm(investment_firm_id):
    investment_firm = InvestmentFirm.get_by_id(investment_firm_id)
    if not investment_firm:
        abort(404)

    db.session.delete(investment_firm)
    db.session.commit()

    return redirect(url_for("admin.get_all_investment_firms"))


@admin.route("/users/")
@is_admin
def get_all_users():
    user_list = UserInfo.get_all()
    return render_template("admin/get_users.html", users=user_list)


@admin.route("/user/edit/<int:user_id>", methods=["GET", "POST"])
@is_admin
def edit_user(user_id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    user = User.get_by_id(user_id)
    if not user:
        status = Status(StatusType.ERROR, "User does not exist.").get_status()
        return redirect(url_for("admin.get_all_users", _external=False, user_id=user_id, **status))

    user_info = UserInfo.get_by_user_id(user_id)
    if not user_info:
        status = Status(StatusType.ERROR, "User info does not exist.").get_status()
        return redirect(url_for("admin.get_all_users", _external=False, user_id=user_id, **status))

    user_payment = UserPayment.get_by_user_id(user_id)
    if not user_payment:
        status = Status(StatusType.ERROR, "User payment does not exist.").get_status()
        return redirect(url_for("admin.get_all_users", _external=False, user_id=user_id, **status))

    if request.method == "POST":
        email = request.form.get("email")
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        username = request.form.get("username", "").strip()
        tier = request.form.get("tier")

        if not email or not first_name or not last_name or not username or not tier:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(url_for("admin.edit_user", _external=False, user_id=user_id, **status))

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            status = Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status()
            return redirect(url_for("admin.edit_user", _external=False, user_id=user_id, **status))

        if (existing_user := User.get_by_email(email)) and existing_user.id != user_id:
            status = Status(StatusType.ERROR, AUTH_EMAIL_USED).get_status()
            return redirect(url_for("admin.edit_user", _external=False, user_id=user_id, **status))

        if UserInfo.is_taken(username) and user_info.username != username:
            status = Status(StatusType.ERROR, "Username already exists.").get_status()
            return redirect(url_for("admin.edit_user", _external=False, user_id=user_id, **status))

        if pfp_uuid := upload_pfp(request.files["pfp"]):
            user_info.pfp_uuid = pfp_uuid

        try:
            user_info.linkedin = request.form.get("linkedin")
            user_info.instagram = request.form.get("instagram")
            user_info.twitter = request.form.get("twitter")
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("admin.edit_user", _external=False, user_id=user_id, **status))

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

        user_info.is_complete = request.form.get("is_complete", False, type=bool)
        user.is_verified = request.form.get("is_verified", False, type=bool)
        user.is_admin = request.form.get("is_admin", False, type=bool)
        user_payment.is_active = request.form.get("is_active", False, type=bool)

        tier = request.form.get("tier", "elevate")
        if tier not in ["elevate", "connect pro", "boost academy", "free"]:
            status = Status(StatusType.ERROR, "Invalid tier").get_status()
            return redirect(url_for("admin.edit_user", _external=False, user_id=user_id, **status))
        user_payment.tier = Tier(tier)

        db.session.commit()
        return redirect(url_for("admin.get_all_users"))

    return render_template(
        "admin/edit_user.html",
        user=user,
        user_info=user_info,
        user_payment=user_payment,
        languages=language_list,
        status_type=status_type,
        msg=msg,
        Tier=Tier,
    )


@admin.route("/user/delete/<int:user_id>", methods=["POST"])
@is_admin
def delete_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        abort(404)

    user.delete_by_id(user_id)
    return redirect(url_for("admin.get_all_users"))


@admin.route("/companies")
@is_admin
def get_all_companies():
    companies = Company.get_all()
    return render_template("admin/get_companies.html", companies=companies)


@admin.route("/company/add", methods=["GET", "POST"])
@is_admin
def add_company():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    users = User.get_all()
    industries = Industry.get_all()
    rounds = Round.get_all()
    countries = Country.get_all()

    if request.method == "POST":
        name = request.form.get("company-name", "").strip()
        if error := validate_field(name, "Company name", "Company name cannot be empty.", "admin.add_company"):
            return error

        preferred_round_id = request.form.get("round")
        industry_id = request.form.get("industry")

        if not preferred_round_id or not industry_id:
            status = Status(StatusType.ERROR, "Please select rounds and industries.").get_status()
            return redirect(
                url_for(
                    "admin.add_company",
                    _external=False,
                    **status,
                )
            )

        company = Company(
            user_id=request.form.get("user"),
            name=name,
            number_of_employees=request.form.get("number_of_employees"),
            description=request.form.get("description"),
            country_id=request.form.get("country"),
            preferred_round_id=preferred_round_id,
            industry_id=industry_id,
            website=request.form.get("website", ""),
        )

        if pfp := request.files["pfp"]:
            try:
                resized_pfp = prepare_picture(pfp)
                pfp_uuid = upload_blob(resized_pfp.read())
                company.pfp_uuid = str(pfp_uuid)
            except Exception as e:
                print(f"An error occurred: {e}")

        db.session.add(company)
        db.session.commit()
        return redirect(url_for("admin.get_all_companies"))

    return render_template(
        "admin/add_company.html",
        industries=industries,
        rounds=rounds,
        countries=countries,
        users=users,
        status_type=status_type,
        msg=msg,
    )


@admin.route("/company/edit/<int:company_id>", methods=["GET", "POST"])
@is_admin
def edit_company(company_id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    company = Company.get_by_id(company_id)
    if not company:
        abort(404)

    users = User.get_all()
    industries = Industry.get_all()
    rounds = Round.get_all()
    countries = Country.get_all()

    if request.method == "POST":
        name = request.form.get("company-name", "").strip()
        if error := validate_field(
            name, "Company name", "Company name cannot be empty.", "admin.edit_company", company_id=company_id
        ):
            return error

        preferred_round_id = request.form.get("round", type=int)
        industry_id = request.form.get("industry", type=int)

        if not industry_id:
            status = Status(StatusType.ERROR, "Industry ID is required.").get_status()
            return redirect(url_for("admin.edit_company", _external=False, company_id=company_id, **status))

        if not preferred_round_id or not industry_id:
            status = Status(StatusType.ERROR, "Please select rounds and industries.").get_status()
            return redirect(
                url_for(
                    "admin.edit_company",
                    _external=False,
                    company_id=company_id,
                    **status,
                )
            )

        user = request.form.get("user", type=int)
        if not user:
            status = Status(StatusType.ERROR, "User does not exist.").get_status()
            return redirect(url_for("admin.edit_company", _external=False, company_id=company_id, **status))

        country_id = request.form.get("country", type=int)
        if not country_id:
            status = Status(StatusType.ERROR, "Country ID is required.").get_status()
            return redirect(url_for("admin.edit_company", _external=False, company_id=company_id, **status))

        company.user_id = user
        company.name = name
        company.description = request.form.get("description", "")
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
        return redirect(url_for("admin.get_all_companies"))

    return render_template(
        "admin/edit_company.html",
        industries=industries,
        rounds=rounds,
        countries=countries,
        users=users,
        company=company,
        status_type=status_type,
        msg=msg,
    )


@admin.route("/company/delete/<int:company_id>", methods=["POST"])
@is_admin
def delete_company(company_id):
    company = Company.get_by_id(company_id)

    if not company:
        abort(404)

    db.session.delete(company)
    db.session.commit()

    return redirect(url_for("admin.get_all_companies"))
