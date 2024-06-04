from functools import wraps

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
)
from flask_login import current_user

from ..extensions import db
from ..models import (
    Industry,
    InvestmentFirm,
    Investor,
    Notification,
    Round,
    User,
)
from ..utils.enums import (
    NotificationDestination,
    NotificationLayout,
)
from ..utils.errors.error_messages import (
    AUTH_FIELDS_INCOMPLETE,
)

admin = Blueprint("admin", __name__)


def check_admin(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect("/login", code=302)

        if not current_user.is_admin:
            return redirect("/", code=302)

        return func(*args, **kwargs)

    return decorated_function


@admin.route("/investors")
@check_admin
def admin_investor_view():
    investors = Investor.get_all()

    return render_template("admin/investors.html", investors=investors)


@admin.route("/investor/<int:id>")
@check_admin
def edit_investor_view(id):
    notifications = Notification.get_unread(
        current_user.id,
        NotificationDestination.ADMIN,
        is_read=False,
    )

    investor = Investor.get_by_id(id)

    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/edit_investor.html", investor=investor, rounds=rounds, industries=industries, notifications=notifications
    )


@admin.route("/investor/<int:id>", methods=["POST"])
@check_admin
def update_investor(id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    data = request.get_json()

    investor = Investor.get_by_id(id)

    if not investor:
        return jsonify({"message": "Investor not found"}), 404

    first_name = data.get("first_name", investor.first_name)
    last_name = data.get("last_name", investor.last_name)
    firm_name = data.get("firm_name", investor.firm_name)
    about = data.get("about", investor.about)
    website = data.get("website", investor.website)
    linkedin = data.get("linkedin", investor.linkedin)
    twitter = data.get("twitter", investor.twitter)
    email = data.get("email", investor.email)
    phone_number = data.get("phone_number", investor.phone_number)
    n_investments = data.get("n_investments", investor.n_investments)
    n_exits = data.get("n_exits", investor.n_exits)
    min_investment = data.get("min_investment", investor.min_investment)
    max_investment = data.get("max_investment", investor.max_investment)
    location = data.get("location", investor.location)
    selected_round_ids = data.get("round", investor.rounds)
    selected_industry_ids = data.get("industry", investor.industries)

    if (
        not first_name
        or not last_name
        or not firm_name
        or not about
        or not email
        or not phone_number
        or not n_investments
        or not n_exits
        or not min_investment
        or not max_investment
        or not location
        or not selected_round_ids
        or not selected_industry_ids
    ):
        notification = Notification(
            user=authenticated_user,
            json_data=NotificationLayout(title="Error!", msg=AUTH_FIELDS_INCOMPLETE).get_json(),
            destination=NotificationDestination.ADMIN,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(f"/admin/investor/{id}", code=302)

    investor.first_name = first_name
    investor.last_name = last_name
    investor.firm_name = firm_name
    investor.about = about
    investor.website = website
    try:
        investor.linkedin = linkedin
    except Exception as e:
        msg = e
        notification = Notification(
            user=authenticated_user,
            json_data=NotificationLayout(title="Error!", msg=str(msg)).get_json(),
            destination=NotificationDestination.ADMIN,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(f"/admin/investor/{id}", code=302)

    investor.twitter = twitter
    investor.email = email
    investor.phone_number = phone_number
    investor.n_investments = n_investments
    investor.n_exits = n_exits
    investor.min_investment = min_investment
    investor.max_investment = max_investment
    investor.location = location
    investor.rounds = list(Round.get_by_id_list(selected_round_ids))
    investor.industries = list(Industry.get_by_id_list(selected_industry_ids))

    db.session.commit()

    return redirect("/admin/investors", code=302)


@admin.route("/investor/<int:id>/delete", methods=["POST"])
@check_admin
def delete_investor(id):
    investor = Investor.get_by_id(id)

    if not investor:
        return jsonify({"message": "Investor not found"}), 404

    db.session.delete(investor)
    db.session.commit()

    return redirect("/admin", code=302)


@admin.route("/investment-firms")
@check_admin
def admin_investment_firm_view():
    investment_firms = InvestmentFirm.get_all()

    return render_template("admin/investment_firms.html", investment_firms=investment_firms)


@admin.route("/investment-firm/<int:id>")
@check_admin
def edit_investment_firm_view(id):
    investment_firm = InvestmentFirm.get_by_id(id)

    return render_template("admin/edit_investment_firm.html", investment_firm=investment_firm)


@admin.route("/investment-firm/<int:id>", methods=["POST"])
@check_admin
def update_investment_firm(id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    data = request.get_json()

    investment_firm = InvestmentFirm.get_by_id(id)

    if not investment_firm:
        return jsonify({"message": "Investment Firm not found"}), 404

    name = data.get("name", investment_firm.name)
    about = data.get("about", investment_firm.about)
    website = data.get("website", investment_firm.website)
    email = data.get("email", investment_firm.email)
    phone_number = data.get("phone_number", investment_firm.phone_number)
    n_investments = data.get("n_investments", investment_firm.n_investments)
    n_exits = data.get("n_exits", investment_firm.n_exits)
    n_employees = data.get("n_employees", investment_firm.n_employees)
    min_investment = data.get("min_investment", investment_firm.min_investment)
    max_investment = data.get("max_investment", investment_firm.max_investment)
    location = data.get("location", investment_firm.location)

    if (
        not name
        or not about
        or not email
        or not phone_number
        or not n_investments
        or not n_exits
        or not n_employees
        or not min_investment
        or not max_investment
        or not location
    ):
        notification = Notification(
            user=authenticated_user,
            json_data=NotificationLayout(title="Error!", msg=AUTH_FIELDS_INCOMPLETE).get_json(),
            destination=NotificationDestination.ADMIN,
        )
        db.session.add(notification)
        db.session.commit()
        return redirect(f"/admin/investment-firm/{id}", code=302)

    investment_firm.name = name
    investment_firm.about = about
    investment_firm.website = website
    investment_firm.email = email
    investment_firm.phone_number = phone_number
    investment_firm.n_investments = n_investments
    investment_firm.n_exits = n_exits
    investment_firm.n_employees = n_employees
    investment_firm.min_investment = min_investment
    investment_firm.max_investment = max_investment
    investment_firm.location = location

    db.session.commit()

    return redirect("/admin/investment-firms", code=302)
