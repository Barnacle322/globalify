import re

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user

from ..extensions import db
from ..models import (
    Industry,
    InvestmentFirm,
    Investor,
    InvestorBackup,
    InvestorOriginPoint,
    NotableInvestment,
    Round,
    User,
    UserInfo,
)
from ..models.claim import ClaimRequest
from ..schemas.investor import InvestorOriginPointSchema, MiniInvestorSchema, RoundSchema
from ..utils.decorators import check_user_info_complete, check_verification
from ..utils.enums import Status, StatusType
from ..utils.errors.error_messages import (
    AUTH_USERNAME_USED,
    EMPTY_BIO,
    EMPTY_FIRSTNAME,
    EMPTY_LASTNAME,
    EMPTY_USERNAME,
    NO_BACKUP_DATA,
    NO_CLAIMED_INVESTOR_PROFILE,
    PICTURE_NOT_LOADED,
)
from ..utils.scraper import add_https_prefix


# TODO(phase-3): upload via R2 — replace stubs below with real upload_picture / delete_blob_from_url
def _upload_picture(picture):
    raise NotImplementedError("TODO(phase-3): implement upload via R2")


def _delete_blob_from_url(url):
    pass


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

    investor = Investor.get_by_user_id_with_investments(current_user.id)
    has_investor_origin = InvestorOriginPoint.exists(investor.id) if investor else False
    pending_claim_requests = ClaimRequest.get_pending_by_user_id(current_user.id)

    return render_template(
        "settings/general.html",
        user=current_user._get_current_object(),
        investor=investor,
        investor_origin=has_investor_origin,
        pending_claim_requests=pending_claim_requests,
        rounds=Round.get_all(),
        industries=Industry.get_all(),
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


@settings.post("/personal-info")
@login_required
@check_user_info_complete
@check_verification
def change_personal_info():
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    user_info = current_user.user_info

    first_name = request.form.get("first-name")
    if first_name and first_name.strip() != user_info.first_name:
        if first_name == " ":
            status = Status(StatusType.ERROR, EMPTY_FIRSTNAME).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.first_name = first_name.strip()

    last_name = request.form.get("last-name")
    if last_name and last_name.strip() != user_info.last_name:
        if last_name == " ":
            status = Status(StatusType.ERROR, EMPTY_LASTNAME).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.last_name = last_name.strip()

    bio = request.form.get("bio")
    if bio and bio.strip() != user_info.bio:
        if bio == " ":
            status = Status(StatusType.ERROR, EMPTY_BIO).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.bio = bio.strip()
    else:
        user_info.bio = None

    username = request.form.get("username")
    if username and username.strip() != user_info.username:
        if username == " ":
            status = Status(StatusType.ERROR, EMPTY_USERNAME).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        if UserInfo.is_taken(username):
            status = Status(StatusType.ERROR, AUTH_USERNAME_USED).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.username = username.strip()

    if picture := request.files.get("picture"):
        try:
            picture_url = _upload_picture(picture)
            if user_info.picture_url:
                try:
                    _delete_blob_from_url(user_info.picture_url)
                except Exception as e:
                    print(e)
            user_info.picture_url = picture_url
        except Exception as e:
            print(e)
            status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
            return redirect(url_for("settings.index", _external=False, **status))

    if linkedin_url := request.form.get("linkedin"):
        linkedin_url = add_https_prefix(linkedin_url)
        try:
            user_info.linkedin_url = linkedin_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
    else:
        user_info.linkedin_url = None

    if instagram_url := request.form.get("instagram"):
        instagram_url = add_https_prefix(instagram_url)
        try:
            user_info.instagram_url = instagram_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
    else:
        user_info.instagram_url = None

    if twitter_url := request.form.get("twitter"):
        twitter_url = add_https_prefix(twitter_url)
        if "x.com" in twitter_url:
            slug = twitter_url.split("/")[-1]
            twitter_url = f"https://twitter.com/{slug}"
        try:
            user_info.twitter_url = twitter_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
    else:
        user_info.twitter_url = None

    user_info.email_public = bool(request.form.get("email_public"))
    user_info.linkedin_public = bool(request.form.get("linkedin_public"))
    user_info.instagram_public = bool(request.form.get("instagram_public"))
    user_info.twitter_public = bool(request.form.get("twitter_public"))
    db.session.commit()

    status = Status(StatusType.SUCCESS, "Personal info successfully changed.").get_status()
    return redirect(url_for("settings.index", _external=False, **status))


@settings.route("/delete-account", methods=["GET", "POST"])
@login_required
@check_user_info_complete
@check_verification
def delete_account():
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        # NOTE: Decorators hold db session open
        # so we need to close it here to properly delete the user objects
        db.session.close()
        db.session.begin()

        # Access the user_info attribute to add it to the session
        _ = current_user.user_info

        db.session.delete(current_user)
        db.session.commit()
        logout_user()

        return redirect(url_for("main.index", _external=False))

    return render_template("settings/delete_oauth_account.html")


@settings.get("/rounds")
@login_required
@check_user_info_complete
@check_verification
def get_rounds():
    rounds = Round.get_all()

    if not rounds:
        return {"rounds": []}

    rounds = [RoundSchema(id=round.id, name=round.name).model_dump() for round in rounds]

    return jsonify({"rounds": rounds})


@settings.get("/investors")
@login_required
@check_user_info_complete
@check_verification
def investor_list_view():
    if not isinstance(current_user, User):
        return redirect(url_for("search.investor_search"))

    investor_models = Investor.get_all()

    investors = []

    for investor in investor_models:
        investor_schema = MiniInvestorSchema(
            id=investor.id,
            name=investor.full_name,
        )
        investors.append(investor_schema.model_dump())

    return jsonify({"investors": investors})


@settings.get("/investment-firms")
@login_required
@check_user_info_complete
@check_verification
def investment_firms_list_view():
    if not isinstance(current_user, User):
        return redirect(url_for("search.investor_search"))

    investment_firm_models = InvestmentFirm.get_all()

    investment_firms = []

    for investment_firm_model in investment_firm_models:
        investment_firm_schema = MiniInvestorSchema(
            id=investment_firm_model.id,
            name=investment_firm_model.name,
        )
        investment_firms.append(investment_firm_schema.model_dump())

    return jsonify({"investment_firms": investment_firms})


@settings.post("/investor")
@login_required
@check_user_info_complete
@check_verification
def edit_investor():
    investor = Investor.get_by_user_id(current_user.id)

    if not investor:
        return jsonify({"status": "error", "message": "Investor not found."}), 404

    if investor.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Not authorized."}), 401

    form_data = request.get_json()

    first_name = form_data.get("first_name").strip()
    last_name = form_data.get("last_name").strip() or None
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
    is_public = form_data.get("is_public") or False
    website = form_data.get("website") or None
    linkedin = form_data.get("linkedin") or None
    twitter = form_data.get("twitter") or None
    email = form_data.get("email") or None
    phone_number = form_data.get("phone_number") or None

    selected_rounds = list(Round.get_by_id_list(selected_round_ids))
    selected_industries = list(Industry.get_by_id_list(selected_industry_ids))
    selected_notable_investments = list(NotableInvestment.get_by_id_list(selected_notable_investment_ids))

    if not first_name:
        status = Status(StatusType.ERROR, EMPTY_FIRSTNAME).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    if first_name != investor.first_name or last_name != investor.last_name:
        investor.first_name = first_name
        investor.last_name = last_name
        investor.set_slug()

    if website:
        website = add_https_prefix(website)
        try:
            investor.website = website
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=True, **status))
    else:
        investor.website = None

    if linkedin:
        linkedin = add_https_prefix(linkedin)
        try:
            investor.linkedin = linkedin
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=True, **status))
    else:
        investor.linkedin = None

    if twitter:
        twitter = add_https_prefix(twitter)
        try:
            investor.twitter = twitter
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=True, **status))
    else:
        investor.twitter = None

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
    investor.is_public = is_public

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

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    try:
        investor.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor updated.").get_status()
    return redirect(url_for("settings.index", _external=False, **status))


@settings.get("/investor/point-origin")
@login_required
@check_user_info_complete
@check_verification
def investor_point_origin_data():
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    investor = Investor.get_by_user_id(current_user.id)
    if not investor:
        status = Status(StatusType.ERROR, NO_CLAIMED_INVESTOR_PROFILE).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    investor_point_origin = InvestorOriginPoint.get_by_investor_id(investor.id)
    if not investor_point_origin:
        status = Status(StatusType.ERROR, NO_BACKUP_DATA).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    data = InvestorOriginPointSchema(
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
        notable_investments=[ni.name for ni in investor_point_origin.notable_investments],
        rounds=[r.name for r in investor_point_origin.rounds],
        industries=[i.name for i in investor_point_origin.industries],
    )
    return data.model_dump()


@settings.get("/investor/restore")
@login_required
@check_user_info_complete
@check_verification
def restore_investor_data():
    if not isinstance(current_user, User):
        return redirect(url_for("auth.login"))

    investor = current_user.investor
    if not investor:
        status = Status(StatusType.ERROR, NO_CLAIMED_INVESTOR_PROFILE).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    investor_point_origin = InvestorOriginPoint.get_by_investor_id(investor.id)
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
        status = Status(StatusType.ERROR, NO_BACKUP_DATA).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor data restored.").get_status()
    return redirect(url_for("settings.index", _external=False, **status))


@settings.get("/users/search/<search_input>")
@login_required
@check_user_info_complete
@check_verification
def search_user(search_input):
    users = (
        db.session.scalars(
            db.select(User)
            .join(UserInfo, User.id == UserInfo.user_id)
            .where(User.email.contains(search_input))
            .where(User.id != current_user.id)
        )
        .unique()
        .all()
    )

    if not users:
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(email_regex, search_input) and not search_input == current_user.email:
            return jsonify({"search_input": search_input})
        return jsonify({"users": []})

    from ..schemas.user import UserSchema

    user_list = []
    for user in users:
        user_element = UserSchema(
            id=user.id,
            email=user.email,
            picture_url=user.user_info.picture_url,
        )
        user_list.append(user_element.model_dump())
    return jsonify({"users": user_list})
