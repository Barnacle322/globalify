import re

from flask import Blueprint, redirect, render_template, request, url_for

from ..models import Industry, InvestmentFirm, Investor, Round, db
from ..utils.errors.auth_error_messages import AUTH_INVALID_EMAIL
from ..utils.status_enum import Status, StatusType

admin = Blueprint("admin", __name__)


@admin.get("/")
def index():
    investors = Investor.get_pagination()
    return render_template("admin/index.html", investors=investors)


# validations for investors


def validate_field(value, field_name, error_message):
    if not value.strip():
        status = Status(StatusType.ERROR, error_message).get_status()
        return redirect(url_for("admin.index", _external=False, **status))
    if value != value.strip():
        status = Status(StatusType.ERROR, f"{field_name} cannot start or end with spaces.").get_status()
        return redirect(url_for("admin.index", _external=False, **status))
    return None


def validate_url_field(url, field_name, error_message):
    if url and not re.match(r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+", url):
        status = Status(StatusType.ERROR, error_message).get_status()
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
        fields_to_validate = [
            ("first_name", "First name", "First name cannot be empty."),
            ("last_name", "Last name", "Last name cannot be empty."),
        ]

        for field, field_name, error_text in fields_to_validate:
            value = request.form.get(field)
            error = validate_field(value, field_name, error_text)
            if error:
                return error

        email = request.form.get("email")
        if email and not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return redirect(
                url_for("admin.index", _external=False, **Status(StatusType.ERROR, AUTH_INVALID_EMAIL).get_status())
            )

        existing_investor = Investor.query.filter(Investor.email == email).first()
        if existing_investor:
            return redirect(
                url_for(
                    "admin.index", _external=False, **Status(StatusType.ERROR, "Email already exists.").get_status()
                )
            )

        selected_round_ids = request.form.getlist("selected_rounds")
        selected_industry_ids = request.form.getlist("selected_industries")

        selected_rounds = [Round.get_by_id(int(rid)) for rid in selected_round_ids if rid.isdigit()]
        selected_industries = [Industry.get_by_id(int(iid)) for iid in selected_industry_ids if iid.isdigit()]

        if not selected_round_ids or not selected_industry_ids:
            return redirect(
                url_for(
                    "admin.index",
                    _external=False,
                    **Status(StatusType.ERROR, "Please select rounds and industries.").get_status(),
                )
            )

        investor_data = {
            key: request.form.get(key)
            for key in (
                "first_name",
                "last_name",
                "firm_name",
                "about",
                "position",
                "website",
                "linkedin",
                "twitter",
                "email",
                "phone_number",
                "location",
            )
        }
        investor_data.update(
            {
                "n_investments": int(request.form.get("n_investments", 0) or 0),
                "n_exits": int(request.form.get("n_exits", 0)),
                "min_investment": int(request.form.get("min_investment", 0) or 0),
                "max_investment": int(request.form.get("max_investment", 0) or 0),
                "rounds": selected_rounds,
                "industries": selected_industries,
            } # type: ignore
        )

        new_investor = Investor(**investor_data)
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
        fields_to_validate = [
            ("first_name", "First name", "First name cannot be empty."),
            ("last_name", "Last name", "Last name cannot be empty."),
        ]

        for field, field_name, error_text in fields_to_validate:
            value = request.form.get(field)
            error = validate_field(value, field_name, error_text)
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

        investor.first_name = request.form.get("first_name")
        investor.last_name = request.form.get("last_name")
        investor.firm_name = request.form.get("firm_name")
        investor.about = request.form.get("about")
        investor.position = request.form.get("position")
        investor.website = request.form.get("website")
        investor.linkedin = request.form.get("linkedin")
        investor.twitter = request.form.get("twitter")
        investor.email = request.form.get("email")
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


@admin.get("/investment-firms/")
def get_all_investment_firms():
    investment_firms = InvestmentFirm.get_all()
    return render_template("admin/get_investment_firms.html", investment_firms=investment_firms)
