import re

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user

from ..extensions import db
from ..models import (
    Industry,
    Organization,
    Person,
    Round,
    User,
    UserInfo,
    entity_search,
)
from ..models.claim import ClaimRequest
from ..schemas.investor import MiniInvestorSchema, RoundSchema
from ..schemas.user import UserSchema
from ..utils.decorators import check_user_info_complete, check_verification
from ..utils.enums import EntityType, Status, StatusType
from ..utils.errors.error_messages import (
    AUTH_USERNAME_USED,
    EMPTY_BIO,
    EMPTY_FIRSTNAME,
    EMPTY_LASTNAME,
    EMPTY_USERNAME,
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

    investor = Person.get_by_user_id(current_user.id)
    pending_claim_requests = ClaimRequest.get_pending_by_user_id(current_user.id)

    return render_template(
        "settings/general.html",
        user=current_user._get_current_object(),
        investor=investor,
        investor_origin=False,
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

    person_models = Person.get_all()

    investors = []

    for person in person_models:
        investor_schema = MiniInvestorSchema(
            id=person.id,
            name=person.full_name,
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

    org_models = Organization.get_all()

    investment_firms = []

    for org in org_models:
        investment_firm_schema = MiniInvestorSchema(
            id=org.id,
            name=org.name,
        )
        investment_firms.append(investment_firm_schema.model_dump())

    return jsonify({"investment_firms": investment_firms})


@settings.post("/investor")
@login_required
@check_user_info_complete
@check_verification
def edit_investor():
    person = Person.get_by_user_id(current_user.id)

    if not person:
        return jsonify({"status": "error", "message": NO_CLAIMED_INVESTOR_PROFILE}), 404

    if person.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Not authorized."}), 401

    form_data = request.get_json()

    first_name = form_data.get("first_name", "").strip()
    last_name = form_data.get("last_name", "") or None
    if last_name:
        last_name = last_name.strip() or None
    about = form_data.get("about") or None
    is_public = form_data.get("is_public") or False
    website = form_data.get("website") or None
    linkedin = form_data.get("linkedin") or None
    twitter = form_data.get("twitter") or None
    email = form_data.get("email") or None
    phone_number = form_data.get("phone_number") or None

    if not first_name:
        status = Status(StatusType.ERROR, EMPTY_FIRSTNAME).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    if first_name != person.first_name or last_name != person.last_name:
        person.first_name = first_name
        person.last_name = last_name
        person.set_slug()

    if website:
        website = add_https_prefix(website)
        try:
            person.website = website
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=True, **status))
    else:
        person.website = None

    if linkedin:
        linkedin = add_https_prefix(linkedin)
        try:
            person.linkedin = linkedin
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=True, **status))
    else:
        person.linkedin = None

    if twitter:
        twitter = add_https_prefix(twitter)
        try:
            person.twitter = twitter
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.index", _external=True, **status))
    else:
        person.twitter = None

    person.about = about
    person.email = email
    person.phone_number = phone_number
    person.is_public = is_public

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    try:
        entity_search.sync_one(EntityType.PERSON, person.id)
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Investor updated.").get_status()
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

    user_list = []
    for user in users:
        user_element = UserSchema(
            id=user.id,
            email=user.email,
            picture_url=user.user_info.picture_url,
        )
        user_list.append(user_element.model_dump())
    return jsonify({"users": user_list})
