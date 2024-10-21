import re

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, logout_user

from ..extensions import db
from ..models import (
    Company,
    CompanyInvitation,
    Country,
    Industry,
    Investor,
    InvestorBackup,
    InvestorOriginPoint,
    NotableInvestment,
    Round,
    User,
    UserCompany,
    UserInfo,
    UserPayment,
)
from ..schemas.investor import InvestorOriginPointSchema
from ..schemas.user import CompanyInvitationSchema, MemberSchema, UserSchema
from ..utils.enums import CompanyRole, Events, Status, StatusType, Tier
from ..utils.errors.error_messages import (
    AUTH_USERNAME_USED,
    COMPANY_NOT_FOUND,
    COMPANY_PERMISSION_DENIED,
    DELETE_COMPANY_PERMISSION_DENIED,
    EDIT_COMPANY_PERMISSION_DENIED,
    EMPTY_BIO,
    EMPTY_COMPANY_NAME,
    EMPTY_COUNTRY_ID,
    EMPTY_EMAIL_OR_ROLE,
    EMPTY_FIRSTNAME,
    EMPTY_LASTNAME,
    EMPTY_USERNAME,
    INVITATION_NOT_FOUND,
    NO_BACKUP_DATA,
    NO_CLAIMED_INVESTOR_PROFILE,
    NO_ROUND_OR_INDUSTRY,
    NOT_COMPANY_MEMBER,
    NOT_COMPANY_OWNER,
    PICTURE_NOT_LOADED,
    REMOVE_YOURSELF_PERMISSION_DENIED,
    USER_ALREADY_IN_COMPANY,
    USER_ALREADY_INVITED,
)
from ..utils.google_helpers.google_pubsub import send_event
from ..utils.google_helpers.google_storage import delete_blob_from_url, upload_picture
from ..utils.scraper import add_https_prefix
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

    investor = Investor.get_by_user_id_with_investments(current_user.id)
    rounds = Round.get_all()
    industries = Industry.get_all()
    investor_origin = InvestorOriginPoint.exists(investor.id) if investor else False

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    return render_template(
        "settings/general.html",
        user=authenticated_user,
        investor=investor,
        investor_origin=investor_origin,
        rounds=rounds,
        industries=industries,
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
    refuse_all_invitations = request.form.get("refuse_all_invitations")
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
            status = Status(StatusType.ERROR, EMPTY_FIRSTNAME).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.first_name = first_name.strip()

    if last_name and last_name.strip() != user_info.last_name:
        if last_name == " ":
            status = Status(StatusType.ERROR, EMPTY_LASTNAME).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.last_name = last_name.strip()

    if bio and bio.strip() != user_info.bio:
        if bio == " ":
            status = Status(StatusType.ERROR, EMPTY_BIO).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        user_info.bio = bio.strip()

    if username and username.strip() != user_info.username:
        if username == " ":
            status = Status(StatusType.ERROR, EMPTY_USERNAME).get_status()
            return redirect(url_for("settings.index", _external=False, **status))
        if UserInfo.is_taken(username):
            status = Status(StatusType.ERROR, AUTH_USERNAME_USED).get_status()
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
            status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
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
    user_info.refuse_all_invitations = bool(refuse_all_invitations)

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


@settings.get("/companies")
@login_required
@check_user_info_complete
@check_verification
def company_list_view():
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_companies = UserCompany.get_by_user_id(user_id=authenticated_user.id)
    invitations = CompanyInvitation.get_by_email(email=authenticated_user.email)

    company_invitations = []
    if invitations:
        for invitation in invitations:
            company_invitation = CompanyInvitationSchema(
                id=invitation.id,
                name=invitation.company.name,
                picture_url=invitation.company.picture_url,
                role=invitation.role.value,
                company_id=invitation.company.id,
            )
            company_invitations.append(company_invitation.model_dump())

    return render_template(
        "settings/company_list.html",
        companies=user_companies,
        invitations=company_invitations,
    )


@settings.get("/company/<int:company_id>")
@login_required
@check_user_info_complete
@check_verification
def company_info_view(company_id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    company_invitations = CompanyInvitation.get_by_company_id(company_id=company_id)
    company_members = UserCompany.get_members(company_id=company_id)
    members = []
    if company_members:
        for user, user_company in company_members:
            user_info = user.user_info
            user_element = MemberSchema(
                id=user.id,
                name=user_info.full_name,
                picture_url=user_info.picture_url,
                role=user_company.role.value,
            )
            members.append(user_element.model_dump())

    user_company = UserCompany.get_by_user_id_and_company_id(
        user_id=authenticated_user.id, company_id=company_id, get_accepted=True
    )
    if not user_company:
        status = Status(StatusType.ERROR, COMPANY_NOT_FOUND).get_status()
        return redirect(url_for("settings.company_list_view", _external=False, **status))

    company = user_company.company
    user_role = user_company.role.value

    users_in_company = UserCompany.get_user_ids_by_company_id(company_id=company_id)

    return render_template(
        "settings/company.html",
        industries=Industry.get_all(),
        rounds=Round.get_all(),
        countries=Country.get_all(),
        company=company,
        members=members,
        users_in_company=users_in_company,
        company_invitations=company_invitations,
        user_role=user_role,
        status_type=status_type,
        msg=msg,
    )


@settings.post("/company/<int:company_id>")
@login_required
@check_user_info_complete
@check_verification
def change_company_info(company_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_company = UserCompany.get_by_user_id_and_company_id(
        user_id=authenticated_user.id, company_id=company_id, get_accepted=True
    )
    if not user_company:
        status = Status(StatusType.ERROR, COMPANY_NOT_FOUND).get_status()
        return redirect(url_for("settings.company_list_view", _external=False, **status))

    if user_company.role == CompanyRole.TEAM:
        status = Status(StatusType.ERROR, EDIT_COMPANY_PERMISSION_DENIED).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    company = user_company.company

    company_name = request.form.get("company-name", "")
    if company_name and company_name.strip() != company.name:
        if company_name == " ":
            status = Status(StatusType.ERROR, EMPTY_COMPANY_NAME).get_status()
            return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))
        company.name = company_name.strip()

    slug = request.form.get("slug") or None
    if not slug:
        company.set_slug()
    else:
        company.slug = slug

    preferred_round_id = request.form.get("round", type=int)
    industry_id = request.form.get("industry", type=int)

    if not preferred_round_id or not industry_id:
        status = Status(StatusType.ERROR, NO_ROUND_OR_INDUSTRY).get_status()
        return redirect(
            url_for(
                "settings.company_info_view",
                company_id=company_id,
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
            status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
            return redirect(url_for("settings.index", _external=False, **status))

    country_id = request.form.get("country", type=int)
    if not country_id:
        status = Status(StatusType.ERROR, EMPTY_COUNTRY_ID).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    website_url = request.form.get("website", "")
    if website_url:
        website_url = add_https_prefix(website_url)
        try:
            company.website_url = website_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))
    else:
        company.website_url = None

    linkedin_url = request.form.get("linkedin", "")
    if linkedin_url:
        linkedin_url = add_https_prefix(linkedin_url)
        try:
            company.linkedin_url = linkedin_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))
    else:
        company.linkedin_url = None

    instagram_url = request.form.get("instagram", "")
    if instagram_url:
        instagram_url = add_https_prefix(instagram_url)
        try:
            company.instagram_url = instagram_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))
    else:
        company.instagram_url = None

    twitter_url = request.form.get("twitter", "")
    if twitter_url:
        twitter_url = add_https_prefix(twitter_url)
        try:
            company.twitter_url = twitter_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))
    else:
        company.twitter_url = None

    if user_company.role in [CompanyRole.OWNER, CompanyRole.ADMIN]:
        is_public = request.form.get("is_public", False, type=bool)
        if is_public is False:
            UserCompany.set_is_public_false_by_company_id(company_id=company_id)
    else:
        status = Status(StatusType.ERROR, EDIT_COMPANY_PERMISSION_DENIED).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    company.description = request.form.get("description", "").strip()
    company.number_of_employees = request.form.get("number_of_employees", 0, type=int)
    company.country_id = country_id
    company.preferred_round_id = preferred_round_id
    company.industry_id = industry_id
    company.coordinates = Country.get_by_id(country_id).name  # type: ignore
    company.is_public = is_public

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    try:
        company.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    status = Status(StatusType.SUCCESS, "Company successfully changed.").get_status()
    return redirect(
        url_for(
            "settings.company_info_view",
            company_id=company_id,
            _external=False,
            **status,
        )
    )


@settings.get("/company/create")
@login_required
@check_user_info_complete
@check_verification
def create_company_view():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")
    industries = Industry.get_all()
    rounds = Round.get_all()
    countries = Country.get_all()

    return render_template(
        "settings/create_company.html",
        industries=industries,
        rounds=rounds,
        countries=countries,
        status_type=status_type,
        msg=msg,
    )


@settings.post("/company/create")
@login_required
@check_user_info_complete
@check_verification
def create_company():
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    form_data = request.form

    company_name = form_data.get("company_name")
    if not company_name:
        status = Status(StatusType.ERROR, EMPTY_COMPANY_NAME).get_status()
        return redirect(url_for("settings.create_company_view", _external=False, **status))

    company = Company(
        name=company_name,
    )

    picture = request.files.get("picture") or None
    if picture:
        try:
            picture_url = upload_picture(picture)
            company.picture_url = picture_url
        except Exception as e:
            print(e)
            status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
            return redirect(url_for("settings.create_company_view", _external=False, **status))

    preferred_round_id = request.form.get("round", type=int)
    industry_id = request.form.get("industry", type=int)

    if not preferred_round_id or not industry_id:
        status = Status(StatusType.ERROR, NO_ROUND_OR_INDUSTRY).get_status()
        return redirect(url_for("settings.create_company_view", _external=False, **status))

    country_id = request.form.get("country", type=int)
    if not country_id:
        status = Status(StatusType.ERROR, EMPTY_COUNTRY_ID).get_status()
        return redirect(url_for("settings.create_company_view", _external=False, **status))

    company.description = form_data.get("description") or None
    company.number_of_employees = form_data.get("number_of_employees", 0, type=int)
    company.website_url = form_data.get("website") or None
    company.preferred_round_id = preferred_round_id
    company.industry_id = industry_id
    company.country_id = country_id
    company.coordinates = Country.get_by_id(country_id).name  # type: ignore

    if not company.slug:
        company.set_slug()

    try:
        db.session.add(company)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.create_company_view", _external=False, **status))

    try:
        company.upsert_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.create_company_view", _external=False, **status))

    existing_user_companies = UserCompany.get_by_user_id(user_id=authenticated_user.id)
    is_primary = False if existing_user_companies else True

    user_company = UserCompany(
        user_id=authenticated_user.id,
        company_id=company.id,
        role=CompanyRole.OWNER,
        is_primary=is_primary,
    )

    try:
        db.session.add(user_company)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.create_company_view", _external=False, **status))
    status = Status(StatusType.SUCCESS, "Company created.").get_status()
    return redirect(url_for("settings.company_list_view", _external=False, **status))


@settings.post("/company/<int:id>/delete")
@login_required
@check_user_info_complete
@check_verification
def delete_company(id):
    company = Company.get_by_id(id)

    user_company = UserCompany.get_by_user_id_and_company_id(user_id=current_user.id, company_id=id)

    if not user_company:
        status = Status(StatusType.ERROR, DELETE_COMPANY_PERMISSION_DENIED).get_status()
        return redirect(url_for("settings.company_list_view", _external=True, **status))

    if user_company.role != CompanyRole.OWNER:
        status = Status(StatusType.ERROR, NOT_COMPANY_OWNER).get_status()
        return redirect(url_for("settings.company_list_view", _external=False, **status))

    if not company:
        status = Status(StatusType.ERROR, COMPANY_NOT_FOUND).get_status()
        return redirect(url_for("settings.company_list_view", _external=True, **status))

    try:
        company.delete_data()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.company_list_view", _external=True, **status))

    try:
        db.session.delete(company)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("settings.company_list_view", _external=True, **status))

    status = Status(StatusType.SUCCESS, "Company deleted.").get_status()  ###
    return redirect(url_for("settings.company_list_view", _external=True, **status))


@settings.post("/company/<int:company_id>/invitation/create")
@login_required
@check_user_info_complete
@check_verification
def invite_user(company_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    user_companies = UserCompany.get_by_company_id_and_role(company_id=company_id, role=CompanyRole.OWNER)
    owner_id_list = [user_company.user_id for user_company in user_companies]

    if authenticated_user.id not in owner_id_list:
        status = Status(StatusType.ERROR, COMPANY_PERMISSION_DENIED).get_status()
        return redirect(url_for("settings.company_info_view", _external=False, **status))

    form_data = request.get_json()
    user_email = form_data.get("email") or None
    user_role = form_data.get("role") or None
    invitation_message = form_data.get("invitation_message") or "Hey, join our company!"

    if not user_email or not user_role:
        status = Status(StatusType.ERROR, EMPTY_EMAIL_OR_ROLE).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    existing_company_invitation = CompanyInvitation.get_by_company_id_and_email(company_id=company_id, email=user_email)
    if existing_company_invitation:
        status = Status(StatusType.ERROR, USER_ALREADY_INVITED).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    existing_user_company = UserCompany.get_by_company_id_and_email(email=user_email, company_id=company_id)
    if existing_user_company:
        status = Status(StatusType.ERROR, USER_ALREADY_IN_COMPANY).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    send_event(
        "A user has been invited to a company.",
        email=user_email,
        event_type=Events.COMPANY_INVITATION.value,
        role=user_role.title(),
        message=invitation_message,
        company_name=Company.get_by_id(company_id).name,  # type: ignore
        invited_by=authenticated_user.user_info.username,  # type: ignore
    )

    company_invitation = CompanyInvitation(
        company_id=company_id,
        email=user_email,
        role=CompanyRole(user_role),
        invited_by=authenticated_user.id,
        message=invitation_message,
    )

    db.session.add(company_invitation)
    db.session.commit()

    status = Status(StatusType.SUCCESS, "User invited.").get_status()
    return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))


@settings.post("/company/<int:company_id>/invitation/accept")
@login_required
@check_user_info_complete
@check_verification
def accept_invitation(company_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    company_invitation = CompanyInvitation.get_by_company_id_and_email(
        company_id=company_id, email=authenticated_user.email
    )
    if not company_invitation:
        status = Status(StatusType.ERROR, INVITATION_NOT_FOUND).get_status()
        return redirect(url_for("settings.company_list_view", _external=False, **status))

    user_company = UserCompany.get_by_user_id_and_company_id(company_id=company_id, user_id=authenticated_user.id)
    if not user_company:
        is_primary = not UserCompany.get_by_user_id(user_id=authenticated_user.id)
        user_company = UserCompany(
            user_id=authenticated_user.id,
            company_id=company_id,
            role=company_invitation.role,
            is_primary=is_primary,
        )
        db.session.add(user_company)

    company_invitation.is_used = True
    db.session.commit()

    return redirect(url_for("settings.company_list_view", _external=False))


@settings.post("/company/<int:company_id>/invitation/decline")
@login_required
@check_user_info_complete
@check_verification
def decline_invitation(company_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    company_invitation = CompanyInvitation.get_by_company_id_and_email(
        company_id=company_id, email=authenticated_user.email
    )
    if not company_invitation:
        status = Status(StatusType.ERROR, INVITATION_NOT_FOUND).get_status()
        return redirect(url_for("settings.company_list_view", _external=False, **status))

    company_invitation.is_used = True
    db.session.commit()

    return redirect(url_for("settings.company_list_view", _external=False))


@settings.post("/companies/invitation/<int:invitation_id>/cancel")
@login_required
@check_user_info_complete
@check_verification
def cancel_invitation(invitation_id):
    company_invitation = CompanyInvitation.get_by_id(id=invitation_id)
    if not company_invitation:
        status = Status(StatusType.ERROR, INVITATION_NOT_FOUND).get_status()
        return redirect(url_for("settings.company_list_view", _external=False, **status))

    authenticated_user: User = current_user._get_current_object()  # type: ignore
    user_companies = UserCompany.get_by_company_id_and_role(
        company_id=company_invitation.company_id, role=CompanyRole.OWNER
    )
    owner_id_list = [user_company.user_id for user_company in user_companies]
    if authenticated_user.id not in owner_id_list:
        status = Status(StatusType.ERROR, COMPANY_PERMISSION_DENIED).get_status()
        return redirect(url_for("settings.company_list_view", _external=False, **status))

    db.session.delete(company_invitation)
    db.session.commit()

    return redirect(url_for("settings.company_list_view", _external=False))


@settings.get("/company/<int:company_id>/members")
@login_required
@check_user_info_complete
@check_verification
def get_company_members(company_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    company_members = UserCompany.get_members(company_id=company_id)
    member_id_list = [user_company.user_id for user_company in company_members]
    if not company_members or (authenticated_user.id not in member_id_list):
        return jsonify({"members": []})

    members = []
    for user, user_company in company_members:
        user_element = MemberSchema(
            id=user.id,
            name=user.user_info.full_name,
            picture_url=user.user_info.picture_url,
            role=user_company.role.value,
        )
        members.append(user_element.model_dump())
    return jsonify({"members": members})


@settings.get("/companies/roles")
@login_required
@check_user_info_complete
@check_verification
def get_company_roles():
    return jsonify({"roles": [role.value for role in CompanyRole]})


@settings.post("/company/member/<int:user_id>/role")
@login_required
@check_user_info_complete
@check_verification
def change_company_role(user_id):
    form_data = request.get_json()

    company_id = form_data.get("company_id")
    role = form_data.get("role")

    current_user_company = UserCompany.get_by_user_id_and_company_id(
        user_id=current_user.id, company_id=company_id, get_accepted=True
    )
    if not current_user_company:
        status = Status(StatusType.ERROR, COMPANY_PERMISSION_DENIED).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))
    if current_user_company.role != CompanyRole.OWNER:
        status = Status(StatusType.ERROR, NOT_COMPANY_OWNER).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    user_company = UserCompany.get_by_user_id_and_company_id(user_id, company_id, True)
    if not user_company:
        status = Status(StatusType.ERROR, NOT_COMPANY_MEMBER).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    user_company.role = CompanyRole(role)
    db.session.commit()

    status = Status(StatusType.SUCCESS, "Member's role has been modified!").get_status()
    return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))


@settings.post("/company/member/<int:user_id>/remove")
@login_required
@check_user_info_complete
@check_verification
def remove_company_member(user_id):
    form_data = request.get_json()
    company_id = form_data.get("company_id")
    if current_user.id == user_id:
        status = Status(StatusType.ERROR, REMOVE_YOURSELF_PERMISSION_DENIED).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    current_user_company = UserCompany.get_by_user_id_and_company_id(
        user_id=current_user.id, company_id=company_id, get_accepted=True
    )
    if not current_user_company:
        status = Status(StatusType.ERROR, COMPANY_PERMISSION_DENIED).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))
    if current_user_company.role != CompanyRole.OWNER:
        status = Status(StatusType.ERROR, NOT_COMPANY_OWNER).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    user_company = UserCompany.get_by_user_id_and_company_id(user_id=user_id, company_id=company_id, get_accepted=True)
    if not user_company:
        status = Status(StatusType.ERROR, NOT_COMPANY_MEMBER).get_status()
        return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))

    company_invitation = CompanyInvitation.get_by_company_id_and_email(
        company_id=company_id, email=user_company.user.email
    )
    if company_invitation:
        db.session.delete(company_invitation)

    db.session.delete(user_company)
    db.session.commit()

    status = Status(StatusType.SUCCESS, "Member removed.").get_status()
    return redirect(url_for("settings.company_info_view", company_id=company_id, _external=False, **status))


@settings.post("/company/<int:company_id>/set-primary")
@login_required
@check_user_info_complete
@check_verification
def make_company_primary(company_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    user_company = UserCompany.get_by_user_id_and_company_id(user_id=authenticated_user.id, company_id=company_id)
    if not user_company:
        status = Status(StatusType.ERROR, COMPANY_NOT_FOUND).get_status()
        return redirect(url_for("settings.company_list_view", _external=False, **status))

    user_company.set_primary = authenticated_user.id

    return redirect(url_for("settings.company_list_view", _external=False))


@settings.post("/company/<int:company_id>/toggle-public")
@login_required
@check_user_info_complete
@check_verification
def make_company_public(company_id):
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    user_company = UserCompany.get_by_user_id_and_company_id(user_id=authenticated_user.id, company_id=company_id)

    if not user_company:
        status = Status(StatusType.ERROR, COMPANY_NOT_FOUND).get_status()
        return redirect(url_for("settings.company_list_view", _external=False, **status))

    user_company.is_public = not user_company.is_public
    db.session.commit()

    return redirect(url_for("settings.company_list_view", _external=False))


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

    # existing_email = User.get_by_email(email) if email else None
    # if existing_email and existing_email.id != investor.user_id:
    #     status = Status(StatusType.ERROR, EMAIL_ALREADY_USED).get_status()
    #     return redirect(url_for("settings.index", _external=True, **status))

    if not first_name:
        status = Status(StatusType.ERROR, EMPTY_FIRSTNAME).get_status()
        return redirect(url_for("settings.index", _external=True, **status))

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
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    investor = Investor.get_by_user_id(authenticated_user.id)
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
    authenticated_user: User = current_user._get_current_object()  # type: ignore

    investor = Investor.get_by_user_id(authenticated_user.id)
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
    users = db.session.scalars(
        db.select(User)
        .join(UserInfo, User.id == UserInfo.user_id)
        .where(User.email.contains(search_input))
        .where(User.id != current_user.id)
        .where(UserInfo.refuse_all_invitations.is_(False))
    ).all()

    if not users:
        email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(email_regex, search_input):
            return jsonify({"search_input": search_input})
        return jsonify({"users": []})

    user_list = []
    for user in users:
        user_element = UserSchema(
            id=user.id,
            email=user.email,
            picture_url=user.user_info.picture_url,  # type: ignore
        )
        user_list.append(user_element.model_dump())
    return jsonify({"users": user_list})
