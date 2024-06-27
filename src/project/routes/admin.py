from datetime import UTC, datetime
from functools import wraps

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import select

from ..extensions import db
from ..models import (
    ClaimRequest,
    Industry,
    InvestmentFirm,
    Investor,
    InvestorBackup,
    InvestorPointOrigin,
    NotableInvestment,
    Round,
    User,
)
from ..routes.main import generate_pagination
from ..utils.enums import (
    RequestStatus,
    Status,
    StatusType,
)

admin = Blueprint("admin", __name__)


def admin_only(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect("/login", code=302)

        if not current_user.is_admin:
            return redirect("/", code=302)

        return func(*args, **kwargs)

    return decorated_function


@admin.get("/investors")
@admin_only
def admin_investor_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    search_string = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)

    query_by = [
        "location",
        "country",
        "rounds",
        "industries",
        "notable_investments",
        "name",
        "firm_name",
        "position",
    ]

    result = Investor.get_search(
        query_string=search_string,
        query_by=query_by,
        page=page,
        per_page=9,
    )
    investors = result.get("investors")

    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    return render_template(
        "admin/investors.html",
        investors=investors,
        query=search_string,
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        status_type=status_type,
        msg=msg,
    )


@admin.get("/investor/<int:id>")
@admin_only
def update_investor_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investor = Investor.get_by_id(id)
    if not investor:
        status = Status(StatusType.ERROR, "Investor not found").get_status()
        return redirect(url_for("admin.admin_investor_view", _external=True, **status))

    notable_investments = NotableInvestment.get_all()
    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/update_investor.html",
        investor=investor,
        rounds=rounds,
        industries=industries,
        notable_investments=notable_investments,
        status_type=status_type,
        msg=msg,
    )


@admin.post("/investor/<int:id>")
@admin_only
def update_investor(id):
    form_data = request.get_json()

    investor = Investor.get_by_id(id)
    if not investor:
        status = Status(StatusType.ERROR, "Investor not found").get_status()
        return redirect(url_for("admin.admin_investor_view", _external=True, **status))

    first_name = form_data.get("first_name", investor.first_name)
    last_name = form_data.get("last_name", investor.last_name)
    slug = form_data.get("slug", investor.slug) or None
    firm_name = form_data.get("firm_name", investor.firm_name) or None
    position = form_data.get("position", investor.position) or None
    about = form_data.get("about", investor.about) or None
    location = form_data.get("location", investor.location) or None

    n_investments = int(form_data.get("n_investments", investor.n_investments) or 0)
    n_exits = int(form_data.get("n_exits", investor.n_exits) or 0)
    min_investment = int(form_data.get("min_investment", investor.min_investment) or 0)
    max_investment = int(form_data.get("max_investment", investor.max_investment) or 0)

    selected_round_ids = form_data.get("rounds", investor.rounds) or []
    selected_industry_ids = form_data.get("industries", investor.industries) or []
    selected_notable_investment_ids = form_data.get("notable_investments", investor.notable_investments) or []

    website = form_data.get("website", investor.website) or None
    linkedin = form_data.get("linkedin", investor.linkedin) or None
    twitter = form_data.get("twitter", investor.twitter) or None
    email = form_data.get("email", investor.email) or None
    phone_number = form_data.get("phone_number", investor.phone_number) or None
    user_email = form_data.get("user_email", investor.user_id) or None

    if not first_name:
        status = Status(StatusType.ERROR, "First name cannot be empty!").get_status()
        return redirect(url_for("admin.create_investor_view", _external=True, **status))

    if email:
        existing_email = User.get_by_email(email)
        if existing_email and existing_email.id != investor.user_id:
            status = Status(StatusType.ERROR, "Email already exists").get_status()
            return redirect(url_for("admin.update_investor_view", id=id, _external=True, **status))

    investor_backup = InvestorBackup.get_by_investor_id(investor.id)
    if not investor_backup:
        investor_backup = InvestorBackup(investor=investor)
    investor_backup.first_name = investor.first_name
    investor_backup.last_name = investor.last_name
    investor_backup.slug = investor.slug
    investor_backup.firm_name = investor.firm_name
    investor_backup.about = investor.about
    investor_backup.position = investor.position
    investor_backup.website = investor.website
    investor_backup.linkedin = investor.linkedin
    investor_backup.twitter = investor.twitter
    investor_backup.email = investor.email
    investor_backup.phone_number = investor.phone_number
    investor_backup.n_investments = investor.n_investments
    investor_backup.n_exits = investor.n_exits
    investor_backup.min_investment = investor.min_investment
    investor_backup.max_investment = investor.max_investment
    investor_backup.location = investor.location
    investor_backup.notable_investments = investor.notable_investments
    investor_backup.rounds = investor.rounds
    investor_backup.industries = investor.industries
    investor_backup.user = investor.user

    db.session.add(investor_backup)

    # Claim investor profile to specific user and initiate point origin
    # if we delete user, point origin will be deleted as well
    user = User.get_by_email(form_data.get("user_email"))
    if user:
        investor.user = user
        investor_point_origin = InvestorPointOrigin.get_by_investor_id(investor.id)
        if not investor_point_origin:
            investor_point_origin = InvestorPointOrigin(investor_id=investor.id)
            investor_point_origin.first_name = investor.first_name
            investor_point_origin.last_name = investor.last_name
            investor_point_origin.slug = investor.slug
            investor_point_origin.firm_name = investor.firm_name
            investor_point_origin.about = investor.about
            investor_point_origin.position = investor.position
            investor_point_origin.website = investor.website
            investor_point_origin.linkedin = investor.linkedin
            investor_point_origin.twitter = investor.twitter
            investor_point_origin.email = investor.email
            investor_point_origin.phone_number = investor.phone_number
            investor_point_origin.n_investments = investor.n_investments
            investor_point_origin.n_exits = investor.n_exits
            investor_point_origin.min_investment = investor.min_investment
            investor_point_origin.max_investment = investor.max_investment
            investor_point_origin.location = investor.location
            investor_point_origin.notable_investments = investor.notable_investments
            investor_point_origin.rounds = investor.rounds
            investor_point_origin.industries = investor.industries
            db.session.add(investor_point_origin)
    else:
        investor.user = None
        investor_point_origin = InvestorPointOrigin.get_by_investor_id(investor.id)
        if investor_point_origin:
            db.session.delete(investor_point_origin)

    investor.first_name = first_name
    investor.last_name = last_name

    if not slug:
        investor.set_slug()
    else:
        investor.slug = slug

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
    investor.rounds = list(Round.get_by_id_list(selected_round_ids))
    investor.industries = list(Industry.get_by_id_list(selected_industry_ids))
    investor.notable_investments = list(NotableInvestment.get_by_id_list(selected_notable_investment_ids))

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.update_investor_view", id=id, _external=True, **status))

    try:
        investor.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.update_investor_view", id=id, _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor updated successfully!").get_status()
    return redirect(url_for("admin.update_investor_view", id=id, _external=True, **status))


@admin.post("/investor/<int:id>/undo")
@admin_only
def undo_investor_data(id):
    investor = Investor.get_by_id(id)
    if not investor:
        status = Status(StatusType.ERROR, "Investor not found").get_status()
        return redirect(url_for("admin.admin_investor_view", _external=True, **status))

    investor_backup = InvestorBackup.get_by_investor_id(investor.id)
    if not investor_backup:
        status = Status(StatusType.ERROR, "Investor backup not found").get_status()
        return redirect(url_for("admin.admin_investor_view", _external=True, **status))

    investor.first_name = investor_backup.first_name
    investor.last_name = investor_backup.last_name
    investor.slug = investor_backup.slug
    investor.firm_name = investor_backup.firm_name
    investor.position = investor_backup.position
    investor.about = investor_backup.about
    investor.website = investor_backup.website
    investor.linkedin = investor_backup.linkedin
    investor.twitter = investor_backup.twitter
    investor.email = investor_backup.email
    investor.phone_number = investor_backup.phone_number
    investor.n_investments = investor_backup.n_investments
    investor.n_exits = investor_backup.n_exits
    investor.min_investment = investor_backup.min_investment
    investor.max_investment = investor_backup.max_investment
    investor.location = investor_backup.location
    investor.rounds = investor_backup.rounds
    investor.industries = investor_backup.industries
    investor.notable_investments = investor_backup.notable_investments
    investor.user = investor_backup.user

    db.session.commit()

    investor.upsert_data()

    status = Status(StatusType.SUCCESS, "Investor backed up successfully!").get_status()

    return redirect(url_for("admin.update_investor_view", id=id, _external=True, **status))


@admin.get("/investor/<int:id>/restore")
@admin_only
def restore_investor_data(id):
    investor = Investor.get_by_id(id)
    if not investor:
        status = Status(StatusType.ERROR, "There is no such investor").get_status()
        return redirect(url_for("admin.admin_investor_view", _external=True, **status))

    investor_point_origin = InvestorPointOrigin.get_by_investor_id(id)
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
        return redirect(url_for("admin.admin_investor_view", id=id, _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor data restored.").get_status()
    return redirect(url_for("admin.update_investor_view", id=id, _external=False, **status))


@admin.get("/investor/create")
@admin_only
def create_investor_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    notable_investments = NotableInvestment.get_all()
    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/create_investor.html",
        rounds=rounds,
        industries=industries,
        notable_investments=notable_investments,
        status_type=status_type,
        msg=msg,
    )


@admin.post("/investor/create")
@admin_only
def create_investor():
    form_data = request.get_json()

    first_name = form_data.get("first_name")
    last_name = form_data.get("last_name")
    slug = form_data.get("slug") or None
    firm_name = form_data.get("firm_name") or None
    position = form_data.get("position") or None
    about = form_data.get("about") or None
    location = form_data.get("location") or None

    n_investments = int(form_data.get("n_investments") or 0)
    n_exits = int(form_data.get("n_exits") or 0)
    min_investment = int(form_data.get("min_investment") or 0)
    max_investment = int(form_data.get("max_investment") or 0)

    selected_round_ids = form_data.get("rounds") or []
    selected_industry_ids = form_data.get("industries") or [""]
    selected_notable_investment_ids = form_data.get("notable_investments") or []

    website = form_data.get("website") or None
    linkedin = form_data.get("linkedin") or None
    twitter = form_data.get("twitter") or None
    email = form_data.get("email") or None
    phone_number = form_data.get("phone_number") or None

    if not first_name:
        status = Status(StatusType.ERROR, "First name cannot be empty!").get_status()
        return redirect(url_for("admin.create_investor_view", _external=True, **status))

    if email:
        existing_email = Investor.get_by_email(email)
        if existing_email:
            status = Status(StatusType.ERROR, "Email already exists").get_status()
            return redirect(url_for("admin.create_investor_view", _external=True, **status))

    investor = Investor(
        first_name=first_name,
        last_name=last_name,
        slug=slug,
        firm_name=firm_name,
        position=position,
        about=about,
        website=website,
        linkedin=linkedin,
        twitter=twitter,
        email=email,
        phone_number=phone_number,
        n_investments=n_investments,
        n_exits=n_exits,
        min_investment=min_investment,
        max_investment=max_investment,
        location=location,
        rounds=list(Round.get_by_id_list(selected_round_ids)),
        industries=list(Industry.get_by_id_list(selected_industry_ids)),
        notable_investments=list(NotableInvestment.get_by_id_list(selected_notable_investment_ids)),
    )

    try:
        db.session.add(investor)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.create_investor_view", _external=True, **status))

    if not investor.slug:
        investor.set_slug()

    try:
        investor.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.create_investor_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor created successfully!").get_status()
    return redirect(url_for("admin.admin_investor_view", _external=True, **status))


@admin.post("/investor/<int:id>/delete")
@admin_only
def delete_investor(id):
    investor = Investor.get_by_id(id)

    investor = Investor.get_by_id(id)
    if not investor:
        status = Status(StatusType.ERROR, "Investor not found").get_status()
        return redirect(url_for("admin.admin_investor_view", _external=True, **status))

    try:
        investor.delete_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.admin_investor_view", _external=True, **status))

    try:
        db.session.delete(investor)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.admin_investor_view", _external=True, **status))

    return redirect("/admin/investors", code=302)


@admin.get("/investment-firms")
@admin_only
def admin_investment_firm_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    search_string = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)

    query_by = [
        "location",
        "country",
        "rounds",
        "industries",
        "embedding",
        "notable_investments",
        "name",
    ]

    result = InvestmentFirm.get_search(
        query_string=search_string,
        query_by=query_by,
        page=page,
        per_page=9,
    )
    investment_firms = result.get("investment_firms")

    pagination = generate_pagination(int(result.get("page", 1)), int(result.get("pages", 1)))

    return render_template(
        "admin/investment_firms.html",
        investment_firms=investment_firms,
        query=search_string,
        pagination=pagination,
        total_pages=len(pagination.get("pages", [])),
        status_type=status_type,
        msg=msg,
    )


@admin.get("/investment-firm/<int:id>")
@admin_only
def update_investment_firm_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    investment_firm = InvestmentFirm.get_by_id(id)
    if not investment_firm:
        status = Status(StatusType.ERROR, "Investment Firm not found").get_status()
        return redirect(url_for("admin.admin_investment_firm_view", _external=True, **status))

    notable_investments = NotableInvestment.get_all()
    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/update_investment_firm.html",
        investment_firm=investment_firm,
        rounds=rounds,
        industries=industries,
        notable_investments=notable_investments,
        status_type=status_type,
        msg=msg,
    )


@admin.post("/investment-firm/<int:id>")
@admin_only
def update_investment_firm(id):
    form_data = request.get_json()

    investment_firm = InvestmentFirm.get_by_id(id)

    if not investment_firm:
        status = Status(StatusType.ERROR, "Investment Firm not found").get_status()
        return redirect(url_for("admin.admin_investment_firm_view", _external=True, **status))

    name = form_data.get("name", investment_firm.name)
    slug = form_data.get("slug", investment_firm.slug) or None

    about = form_data.get("about", investment_firm.about) or None
    location = form_data.get("location", investment_firm.location) or None

    selected_round_ids = form_data.get("rounds", investment_firm.rounds) or []
    selected_industry_ids = form_data.get("industries", investment_firm.industries) or []
    selected_notable_investment_ids = form_data.get("notable_investments", investment_firm.notable_investments) or []

    n_investments = int(form_data.get("n_investments", investment_firm.n_investments) or 0)
    n_exits = int(form_data.get("n_exits", investment_firm.n_exits) or 0)
    n_employees = int(form_data.get("n_employees", investment_firm.n_employees) or 0)
    min_investment = int(form_data.get("min_investment", investment_firm.min_investment) or 0)
    max_investment = int(form_data.get("max_investment", investment_firm.max_investment) or 0)

    website = form_data.get("website", investment_firm.website) or None
    email = form_data.get("email", investment_firm.email) or None
    phone_number = form_data.get("phone_number", investment_firm.phone_number) or None

    if not name:
        status = Status(StatusType.ERROR, "Name cannot be empty!").get_status()
        return redirect(url_for("admin.update_investment_firm_view", id=id, _external=True, **status))

    if not slug:
        investment_firm.set_slug()
    else:
        investment_firm.slug = slug

    if email:
        existing_email = InvestmentFirm.get_by_email(email)
        if existing_email and existing_email.id != investment_firm.id:
            status = Status(StatusType.ERROR, "Email already exists").get_status()
            return redirect(url_for("admin.update_investment_firm_view", id=id, _external=True, **status))

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
    investment_firm.rounds = list(Round.get_by_id_list(selected_round_ids))
    investment_firm.industries = list(Industry.get_by_id_list(selected_industry_ids))
    investment_firm.notable_investments = list(NotableInvestment.get_by_id_list(selected_notable_investment_ids))

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.update_investment_firm_view", id=id, _external=True, **status))

    try:
        investment_firm.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.update_investment_firm_view", id=id, _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investment Firm updated successfully!").get_status()
    return redirect(url_for("admin.update_investment_firm_view", id=id, _external=True, **status))


@admin.get("/investment-firm/create")
@admin_only
def create_investment_firm_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    notable_investments = NotableInvestment.get_all()
    rounds = Round.get_all()
    industries = Industry.get_all()

    return render_template(
        "admin/create_investment_firm.html",
        rounds=rounds,
        industries=industries,
        notable_investments=notable_investments,
        status_type=status_type,
        msg=msg,
    )


@admin.post("/investment-firm/create")
@admin_only
def create_investment_firm():
    form_data = request.get_json()

    name = form_data.get("name")
    slug = form_data.get("slug") or None
    location = form_data.get("location") or None
    about = form_data.get("about") or None

    selected_round_ids = form_data.get("rounds") or []
    selected_industry_ids = form_data.get("industries") or []
    selected_notable_investment_ids = form_data.get("notable_investments") or []

    n_investments = int(form_data.get("n_investments") or 0)
    n_exits = int(form_data.get("n_exits") or 0)
    n_employees = int(form_data.get("n_employees") or 0)
    min_investment = int(form_data.get("min_investment") or 0)
    max_investment = int(form_data.get("max_investment") or 0)

    website = form_data.get("website") or None
    email = form_data.get("email") or None
    phone_number = form_data.get("phone_number") or None

    if not name:
        status = Status(StatusType.ERROR, "Name cannot be empty!").get_status()
        return redirect(url_for("admin.create_investment_firm_view", _external=True, **status))

    if email:
        existing_email = InvestmentFirm.get_by_email(email)
        if existing_email:
            status = Status(StatusType.ERROR, "Email already exists").get_status()
            return redirect(url_for("admin.create_investment_firm_view", _external=True, **status))

    investment_firm = InvestmentFirm(
        name=name,
        slug=slug,
        about=about,
        website=website,
        email=email,
        phone_number=phone_number,
        n_investments=n_investments,
        n_exits=n_exits,
        n_employees=n_employees,
        min_investment=min_investment,
        max_investment=max_investment,
        location=location,
        rounds=list(Round.get_by_id_list(selected_round_ids)),
        industries=list(Industry.get_by_id_list(selected_industry_ids)),
        notable_investments=list(NotableInvestment.get_by_id_list(selected_notable_investment_ids)),
    )

    try:
        db.session.add(investment_firm)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.create_investment_firm_view", _external=True, **status))

    if not investment_firm.slug:
        investment_firm.set_slug()

    try:
        investment_firm.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.create_investment_firm_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investment Firm created successfully!").get_status()
    return redirect(url_for("admin.admin_investment_firm_view", _external=True, **status))


@admin.post("/investment-firm/<int:id>/delete")
@admin_only
def delete_investment_firm(id):
    investment_firm = InvestmentFirm.get_by_id(id)

    if not investment_firm:
        status = Status(StatusType.ERROR, "Investment Firm not found").get_status()
        return redirect(url_for("admin.admin_investment_firm_view", _external=True, **status))

    try:
        investment_firm.delete_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.admin_investment_firm_view", _external=True, **status))

    try:
        db.session.delete(investment_firm)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.admin_investment_firm_view", _external=True, **status))

    return redirect("/admin/investment-firms", code=302)


@admin.get("/search_users/<search_input>")
@admin_only
def search_user(search_input):
    users = db.session.execute(select(User).where(User.email.contains(search_input))).scalars().all()

    return jsonify(users=[user.email for user in users])


@admin.get("/claim-requests")
@admin_only
def claim_requests_view():
    claim_requests = ClaimRequest.get_all()

    return render_template("admin/claim_requests.html", claim_requests=claim_requests)


@admin.post("/claim-request/<int:id>")
@admin_only
def edit_claim_request(id):
    claim_request = ClaimRequest.get_by_id(id)

    if not claim_request:
        status = Status(StatusType.ERROR, "Claim request not found").get_status()
        return redirect(url_for("admin.claim_requests_view", _external=True, **status))

    investor = Investor.get_by_id(claim_request.investor_id)
    if not investor:
        status = Status(StatusType.ERROR, "Investor not found").get_status()
        return redirect(url_for("admin.claim_requests_view", _external=True, **status))

    form_data = request.get_json()
    claim_status = form_data.get("status")

    if claim_status not in ["approved", "rejected"]:
        status = Status(StatusType.ERROR, "Invalid claim status").get_status()
        return redirect(url_for("admin.claim_requests_view", _external=True, **status))
    elif claim_status == "approved":
        claim_request.status = RequestStatus.APPROVED
        claim_request.approved_at = datetime.now(UTC)
        claim_request.approved_by = current_user.user_info.username
        investor.user = claim_request.user
    elif claim_status == "rejected":
        claim_request.status = RequestStatus.REJECTED
        investor.user = None
    db.session.commit()

    return jsonify({"message": "Claim request updated"}), 200
