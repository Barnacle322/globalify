from datetime import datetime

from flask import Blueprint, redirect, render_template, request, url_for
from sqlalchemy import or_

from ...extensions import db
from ...models import User, UserInfo, UserPayment
from ...routes.main import generate_pagination
from ...utils.decorators import admin_only
from ...utils.enums import (
    Status,
    StatusType,
    Tier,
)
from ...utils.errors.error_messages import (
    PICTURE_NOT_LOADED,
    USER_INFO_NOT_FOUND,
    USER_NOT_FOUND,
    USER_PAYMENT_NOT_FOUND,
)
from ...utils.google_helpers.google_storage import delete_blob_from_url, upload_picture
from ...utils.scraper import add_https_prefix

user = Blueprint("user", __name__)


@user.get("/")
@admin_only
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    search_string = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)

    base_query = db.select(User, UserInfo).join(UserInfo, User.id == UserInfo.user_id)

    if search_string:
        base_query = base_query.where(
            or_(UserInfo.first_name.ilike(f"%{search_string}%"), UserInfo.last_name.ilike(f"%{search_string}%"))
        )

    pagination = db.paginate(base_query, page=page, per_page=9, error_out=False)

    user_info = []
    for result in pagination.items:
        user_info.append(
            {
                "id": result.id,
                "email": result.email,
                "first_name": result.user_info.first_name,
                "last_name": result.user_info.last_name,
                "bio": result.user_info.bio,
            }
        )

    total_pages = pagination.pages or 1
    pagination_info = generate_pagination(page, total_pages, 9)

    return render_template(
        "admin/users.html",
        users=user_info,
        query=search_string,
        pagination=pagination_info,
        total_pages=pagination.pages,
        status_type=status_type,
        msg=msg,
    )


@user.get("/<int:id>")
@admin_only
def update_user_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    user = User.get_by_id(id)
    if not user:
        status = Status(StatusType.ERROR, USER_NOT_FOUND).get_status()
        return redirect(url_for("admin.user.index", _external=True, **status))

    user_info = UserInfo.get_by_user_id(id)
    user_payment = UserPayment.get_by_user_id(id)
    tiers = [tier for tier in Tier]  ########

    return render_template(
        "admin/update_user.html",
        user=user,
        user_info=user_info,
        user_payment=user_payment,
        tiers=tiers,
        status_type=status_type,
        msg=msg,
    )


@user.post("/<int:id>")
@admin_only
def update_user(id):
    form_data = request.get_json()

    user = User.get_by_id(id)
    if not user:
        status = Status(StatusType.ERROR, USER_NOT_FOUND).get_status()
        return redirect(url_for("admin.user.index", _external=True, **status))

    user_info = UserInfo.get_by_user_id(id)
    if not user_info:
        status = Status(StatusType.ERROR, USER_INFO_NOT_FOUND).get_status()
        return redirect(url_for("admin.user.index", _external=True, **status))

    user_payment = UserPayment.get_by_user_id(id)
    if not user_payment:
        status = Status(StatusType.ERROR, USER_PAYMENT_NOT_FOUND).get_status()
        return redirect(url_for("admin.user.index", _external=True, **status))

    linkedin_url = form_data.get("linkedin", user_info.linkedin_url) or None
    if linkedin_url:
        linkedin_url = add_https_prefix(linkedin_url)
        try:
            user_info.linkedin_url = linkedin_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("admin.user.update_user_view", id=id, _external=False, **status))
    else:
        user_info.linkedin_url = None

    instagram_url = form_data.get("instagram", user_info.instagram_url) or None
    if instagram_url:
        instagram_url = add_https_prefix(instagram_url)
        try:
            user_info.instagram_url = instagram_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("admin.user.update_user_view", id=id, _external=False, **status))
    else:
        user_info.instagram_url = None

    twitter_url = form_data.get("twitter", user_info.twitter_url) or None
    if twitter_url:
        twitter_url = add_https_prefix(twitter_url)
        try:
            user_info.twitter_url = twitter_url
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("admin.user.update_user_view", id=id, _external=False, **status))
    else:
        user_info.twitter_url = None

    picture = request.files.get("picture") or None
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
            return redirect(url_for("admin.user_info.update_user_info_view", _external=False, **status))

    user.email = form_data.get("email", user.email).strip()
    user.is_verified = form_data.get("is_verified", user.is_verified)
    user.is_admin = form_data.get("is_admin", user.is_admin)

    user_info.first_name = form_data.get("first_name", user_info.first_name).strip()
    user_info.last_name = form_data.get("last_name", user_info.last_name).strip()
    user_info.username = form_data.get("username", user_info.username).strip()
    user_info.bio = form_data.get("bio", user_info.bio)

    user_info.is_complete = form_data.get("is_complete", user_info.is_complete)
    user_info.refuse_all_invitations = form_data.get("refuse_all_invitations", user_info.refuse_all_invitations)
    user_info.email_public = form_data.get("email_public", user_info.email_public)
    user_info.instagram_public = form_data.get("instagram_public", user_info.instagram_public)
    user_info.linkedin_public = form_data.get("linkedin_public", user_info.linkedin_public)
    user_info.twitter_public = form_data.get("twitter_public", user_info.twitter_public)

    user_payment.tier = form_data.get("tier", user_payment.tier)
    user_payment.is_active = form_data.get("is_active", user_payment.is_active)
    user_payment.customer_id = form_data.get("customer_id", user_payment.customer_id)
    user_payment.subscription_id = form_data.get("subscription_id", user_payment.subscription_id)
    created = form_data.get("created", user_payment.created)
    if created:
        user_payment.created = datetime.strptime(created, "%Y-%m-%d")
    expires_at = form_data.get("expires_at", user_payment.expires_at)
    if expires_at:
        user_payment.expires_at = datetime.strptime(expires_at, "%Y-%m-%d")

    try:
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.user.update_user_view", id=id, _external=True, **status))

    status = Status(StatusType.SUCCESS, "User updated successfully!").get_status()
    return redirect(url_for("admin.user.update_user_view", id=id, _external=True, **status))


@user.post("/<int:id>/delete")
@admin_only
def delete_user(id):
    user = User.get_by_id(id)
    if not user:
        status = Status(StatusType.ERROR, USER_NOT_FOUND).get_status()
        return redirect(url_for("admin.user.index", _external=True, **status))

    try:
        user.delete_by_id(id)
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.user.index", _external=True, **status))

    try:
        db.session.delete(user)
        db.session.commit()
    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.user.index", _external=True, **status))

    return redirect(url_for("admin.user.index"), code=302)
