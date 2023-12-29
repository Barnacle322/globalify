import re

from flask import Blueprint, redirect, render_template, request, url_for

from ..extensions import db
from ..models import Industry, InvestmentFirm, Investor, Round, User
from ..utils.errors.auth_error_messages import (
    AUTH_EMAIL_USED,
    AUTH_FIELDS_INCOMPLETE,
    AUTH_INVALID_EMAIL,
    AUTH_MISMATCHED_PASSWORDS,
    AUTH_OAUTH_USED,
)
from ..utils.status_enum import OauthProvider, Status, StatusType

admin = Blueprint("admin", __name__)


# Investors


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


# validations for investors


def validate_field(value, field_name, error_message):
    if not value.strip():
        status = Status(StatusType.ERROR, error_message).get_status()
        return redirect(url_for("admin.index", _external=False, **status))
    if value != value.strip():
        status = Status(StatusType.ERROR, f"{field_name} cannot start or end with spaces.").get_status()
        return redirect(url_for("admin.index", _external=False, **status))
    return None


# investors
@admin.get("/investors/")
def get_all_investors():
    investors = Investor.get_all()
    return render_template("admin/investors.html", investors=investors)


@admin.route("/investor/add", methods=["GET", "POST"])
def add_investor():
    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")

        error = validate_field(first_name, "First name", "First name cannot be empty.")
        if error:
            return error

        error = validate_field(last_name, "Last name", "Last name cannot be empty.")
        if error:
            return error

        email = request.form.get("email")
        if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return redirect(
                url_for("admin.index", _external=False, **Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status())
            )

        existing_investor = Investor.get_by_email(email=email)  # type: ignore
        if existing_investor:
            return redirect(
                url_for(
                    "admin.index", _external=False, **Status(StatusType.ERROR, "Email already exists.").get_status()
                )
            )

        selected_round_ids = request.form.getlist("selected_rounds")
        selected_industry_ids = request.form.getlist("selected_industries")
        print(selected_round_ids)
        print(selected_industry_ids)
        if not selected_round_ids or not selected_industry_ids:
            return redirect(
                url_for(
                    "admin.index",
                    _external=False,
                    **Status(StatusType.ERROR, "Please select rounds and industries.").get_status(),
                )
            )

        n_investments = int(request.form.get("n_investments", 0) or 0)
        n_exits = int(request.form.get("n_exits", 0) or 0)
        min_investment = int(request.form.get("min_investment", 0) or 0)
        max_investment = int(request.form.get("max_investment", 0)or 0)

        selected_rounds = [Round.get_by_id(int(rid)) for rid in selected_round_ids if rid.isdigit()]
        selected_industries = [Industry.get_by_id(int(iid)) for iid in selected_industry_ids if iid.isdigit()]

        new_investor = Investor(
            first_name=first_name,
            last_name=last_name,
            firm_name=request.form.get("firm_name"),
            about=request.form.get("about"),
            position=request.form.get("position"),
            website=request.form.get("website"),
            linkedin=request.form.get("linkedin"),
            twitter=request.form.get("twitter"),
            email=email,
            phone_number=request.form.get("phone_number"),
            location=request.form.get("location"),
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

    return render_template("admin/add_investor.html", rounds=rounds, industries=industries)


@admin.route("/investor/edit/<int:investor_id>", methods=["GET", "POST"])
def edit_investor(investor_id):
    investor = Investor.query.get_or_404(investor_id)

    if request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")

        error = validate_field(first_name, "First name", "First name cannot be empty.")
        if error:
            return error

        error = validate_field(last_name, "Last name", "Last name cannot be empty.")
        if error:
            return error

        email = request.form.get("email")
        if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return redirect(
                url_for("admin.index", _external=False, **Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status())
            )

        existing_investor = Investor.query.filter(Investor.email == email, Investor.id != investor_id).first()
        if existing_investor:
            return redirect(
                url_for(
                    "admin.index", _external=False, **Status(StatusType.ERROR, "Email already exists.").get_status()
                )
            )

        selected_round_ids = request.form.getlist("selected_rounds")
        selected_industry_ids = request.form.getlist("selected_industries")

        if not selected_round_ids or not selected_industry_ids:
            return redirect(
                url_for(
                    "admin.index",
                    _external=False,
                    **Status(StatusType.ERROR, "Please select rounds and industries.").get_status(),
                )
            )

        selected_rounds = [Round.get_by_id(int(round_id)) for round_id in selected_round_ids if round_id.isdigit()]
        selected_industries = [
            Industry.get_by_id(int(industry_id)) for industry_id in selected_industry_ids if industry_id.isdigit()
        ]

        investor.first_name = first_name
        investor.last_name = last_name
        investor.firm_name = request.form.get("firm_name")
        investor.about = request.form.get("about")
        investor.position = request.form.get("position")
        investor.website = request.form.get("website")
        investor.linkedin = request.form.get("linkedin")
        investor.twitter = request.form.get("twitter")
        investor.email = email
        investor.phone_number = request.form.get("phone_number")
        investor.n_investments = int(request.form.get("n_investments", 0) or 0)
        investor.n_exits = int(request.form.get("n_exits", 0) or 0)
        investor.min_investment = int(request.form.get("min_investment", 0) or 0)
        investor.max_investment = int(request.form.get("max_investment", 0) or 0)
        investor.location = request.form.get("location")

        investor.rounds = selected_rounds
        investor.industries = selected_industries

        db.session.commit()

        return redirect(url_for("admin.index"))

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template("admin/edit_investor.html", investor=investor, rounds=rounds, industries=industries)


@admin.route("/investor/delete/<int:investor_id>", methods=["POST"])
def delete_investor(investor_id):
    investor = Investor.query.get_or_404(investor_id)

    db.session.delete(investor)
    db.session.commit()

    return redirect(url_for("admin.index"))


# Investment Firms


@admin.get("/investment-firms")
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
def add_investment_firm():
    if request.method == "POST":
        name = request.form.get("name")

        error = validate_field(name, "Name", "Name cannot be empty.")
        if error:
            return error

        email = request.form.get("email")
        if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return redirect(
                url_for("admin.index", _external=False, **Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status())
            )

        existing_investor = InvestmentFirm.get_by_email(email=email)  # type: ignore
        if existing_investor:
            return redirect(
                url_for(
                    "admin.index", _external=False, **Status(StatusType.ERROR, "Email already exists.").get_status()
                )
            )

        selected_round_ids = request.form.getlist("selected_rounds")
        selected_industry_ids = request.form.getlist("selected_industries")

        if not selected_round_ids or not selected_industry_ids:
            return redirect(
                url_for(
                    "admin.index",
                    _external=False,
                    **Status(StatusType.ERROR, "Please select rounds and industries.").get_status(),
                )
            )

        selected_rounds = [Round.get_by_id(int(rid)) for rid in selected_round_ids if rid.isdigit()]
        selected_industries = [Industry.get_by_id(int(iid)) for iid in selected_industry_ids if iid.isdigit()]

        new_investor = InvestmentFirm(
            name=name,
            about=request.form.get("about"),
            website=request.form.get("website"),
            email=email,
            phone_number=request.form.get("phone_number"),
            n_investments=int(request.form.get("n_investments", 0) or 0),
            n_exits=int(request.form.get("n_exits", 0) or 0),
            n_employees=int(request.form.get("n_employees", 0) or 0),
            min_investment=int(request.form.get("min_investment", 0) or 0),
            max_investment=int(request.form.get("max_investment", 0) or 0),
            rounds=selected_rounds,
            industries=selected_industries,
        )

        db.session.add(new_investor)
        db.session.commit()

        return redirect(url_for("admin.get_all_investment_firms"))

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template("admin/add_investment_firm.html", rounds=rounds, industries=industries)


@admin.route("/investment-firm/edit/<int:investment_firm_id>", methods=["GET", "POST"])
def edit_investment_firm(investment_firm_id):
    investment_firm = InvestmentFirm.query.get_or_404(investment_firm_id)
    if request.method == "POST":
        name = request.form.get("name")
        error = validate_field(name, "Name", "Name cannot be empty.")
        if error:
            return error

        email = request.form.get("email")
        if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return redirect(
                url_for("admin.index", _external=False, **Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status())
            )

        existing_investor = InvestmentFirm.query.filter(
            InvestmentFirm.email == email, InvestmentFirm.id != investment_firm_id
        ).first()
        if existing_investor:
            return redirect(
                url_for(
                    "admin.index", _external=False, **Status(StatusType.ERROR, "Email already exists.").get_status()
                )
            )

        selected_round_ids = request.form.getlist("selected_rounds")
        selected_industry_ids = request.form.getlist("selected_industries")

        if not selected_round_ids or not selected_industry_ids:
            return redirect(
                url_for(
                    "admin.index",
                    _external=False,
                    **Status(StatusType.ERROR, "Please select rounds and industries.").get_status(),
                )
            )

        selected_rounds = [Round.get_by_id(int(round_id)) for round_id in selected_round_ids if round_id.isdigit()]
        selected_industries = [
            Industry.get_by_id(int(industry_id)) for industry_id in selected_industry_ids if industry_id.isdigit()
        ]

        investment_firm.name = name
        investment_firm.about = request.form.get("about")
        investment_firm.website = request.form.get("website")
        investment_firm.email = email
        investment_firm.phone_number = request.form.get("phone_number")
        investment_firm.n_investments = int(request.form.get("n_investments", 0) or 0)
        investment_firm.n_exits = int(request.form.get("n_exits", 0) or 0)
        investment_firm.n_employees = int(request.form.get("n_employees", 0) or 0)
        investment_firm.min_investment = int(request.form.get("min_investment", 0) or 0)
        investment_firm.max_investment = int(request.form.get("max_investment", 0) or 0)

        investment_firm.rounds = selected_rounds
        investment_firm.industries = selected_industries

        db.session.commit()

        return redirect(url_for("admin.get_all_investment_firms"))

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/edit_investment_firm.html", investment_firm=investment_firm, rounds=rounds, industries=industries
    )


@admin.route("/investment-firm/delete/<int:investment_firm_id>", methods=["POST"])
def delete_investment_firm(investment_firm_id):
    investment_firm = InvestmentFirm.query.get_or_404(investment_firm_id)

    db.session.delete(investment_firm)
    db.session.commit()

    return redirect(url_for("admin.get_all_investment_firms"))


# User


@admin.route("/users")
def get_all_users():
    users = User.get_all()

    return render_template("admin/get_users.html", users=users)


@admin.route("/user/add", methods=["GET", "POST"])
def add_user():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not email or not password or not confirm_password:
            status = Status(StatusType.ERROR, AUTH_FIELDS_INCOMPLETE).get_status()
            return redirect(url_for("admin.add_user", _external=False, **status))

        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            status = Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status()
            return redirect(url_for("auth.register", _external=False, **status))

        if password != confirm_password:
            status = Status(StatusType.ERROR, AUTH_MISMATCHED_PASSWORDS).get_status()
            return redirect(url_for("admin.add_user", _external=False, **status))

        if (oauth := User.signed_with_oauth(email)) != OauthProvider.REGULAR:
            status = Status(StatusType.WARNING, AUTH_OAUTH_USED.format(oauth.value.capitalize())).get_status()
            return redirect(url_for("admin.add_user", _external=False, **status))

        user = User.get_by_email(email)
        if user:
            status = Status(StatusType.ERROR, AUTH_EMAIL_USED).get_status()
            return redirect(url_for("admin.add_user", _external=False, **status))

        new_user = User(email=email, oauth_provider=OauthProvider.REGULAR)
        new_user.password = password
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("admin.get_all_users"))
    return render_template("admin/add_user.html")
