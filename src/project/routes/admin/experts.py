import datetime

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from ...extensions import db
from ...models.helpers import Country, Industry
from ...models.superconnect import (
    # Event,
    Expert,
    Qualification,
    # TimeSlot,
)
from ...models.user import Company, Notification, User
from ...schemas.notification import NotificationItem, NotificationLayout
from ...utils.decorators import admin_only
from ...utils.enums import NotificationType, QualificationType, Status, StatusType
from ...utils.errors.error_messages import PICTURE_NOT_LOADED
from ...utils.funcs import generate_pagination
from ...utils.google_helpers.google_storage import upload_picture
from ...utils.scraper import add_https_prefix

expert = Blueprint("experts", __name__)


@expert.get("/")
@admin_only
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    search_string = request.args.get("search", "")
    experts = Expert.get_all()

    return render_template(
        "admin/experts/experts.html",
        experts=experts,
        query=search_string,
        status_type=status_type,
        msg=msg,
    )


@expert.get("/<int:id>")
@admin_only
def update_investor_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    expert = Expert.get_by_id(id)
    if not expert:
        status = Status(StatusType.ERROR, "Expert not found.").get_status()
        return redirect(url_for("admin.expert.index", _external=True, **status))

    return render_template(
        "admin/experts/update_expert.html",
        expert=expert,
        status_type=status_type,
        msg=msg,
    )


@expert.route("/create", methods=["GET", "POST"])
@admin_only
def create_expert():
    if request.method == "GET":
        status_type, msg = None, None
        if query := request.args:
            status_type = query.get("type")
            msg = query.get("msg")

        return render_template(
            "admin/experts/create_expert.html",
            status_type=status_type,
            msg=msg,
        )

    else:
        form_data = request.get_json()
        if not form_data:
            return jsonify({"error": "No data provided"}), 400

        linkedin = form_data.get("linkedin")
        twitter = form_data.get("twitter")
        user_email = form_data.get("user_email")
        picture = request.files.get("picture")
        price_str = form_data.get("price")
        user = None
        if user_email:
            user = User.query.filter_by(email=user_email).first()
            if not user:
                return jsonify({"error": "User with provided email does not exist"}), 400

        picture_url = None
        if picture:
            try:
                picture_url = upload_picture(picture)
            except Exception as e:
                print(e)
                status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
                return redirect(url_for("settings.create_company_view", _external=False, **status))

        price = None
        if price_str and price_str.strip():  # Check if non-empty and non-whitespace
            try:
                price = float(price_str)
                if price < 0:
                    return jsonify({"error": "Price cannot be negative"}), 400
            except ValueError:
                return jsonify({"error": "Invalid price format: must be a number"}), 400

        expert = Expert(
            first_name=form_data.get("first_name") or None,
            last_name=form_data.get("last_name") or None,
            firm_name=form_data.get("firm_name") or None,
            position=form_data.get("position") or None,
            location=form_data.get("location") or None,
            bio=form_data.get("bio") or None,
            price=price,
            description=form_data.get("description") or None,
            linkedin=add_https_prefix(linkedin) if linkedin else None,
            twitter=add_https_prefix(twitter) if twitter else None,
            email=form_data.get("email") or None,
            phone_number=form_data.get("phone_number") or None,
            user_id=user.id if user else None,
            picture_url=picture_url,
            created_at=datetime.datetime.now(),
        )
        db.session.add(expert)
        db.session.commit()

        return jsonify({"message": "Expert created successfully", "id": expert.id}), 201


@expert.post("/update/<int:id>")
@admin_only
def update_expert(id):
    form_data = request.get_json()
    if not form_data:
        return jsonify({"error": "No data provided"}), 400

    expert = Expert.get_by_id(id)
    if not expert:
        return jsonify({"error": "Expert not found"}), 404

    # Update the expert's attributes
    expert.first_name = form_data.get("first_name") or None
    expert.last_name = form_data.get("last_name") or None
    expert.firm_name = form_data.get("firm_name") or None
    expert.position = form_data.get("position") or None
    expert.location = form_data.get("location") or None
    expert.bio = form_data.get("bio") or None
    expert.description = form_data.get("description") or None
    expert.linkedin = add_https_prefix(form_data.get("linkedin")) if form_data.get("linkedin") else None
    expert.twitter = add_https_prefix(form_data.get("twitter")) if form_data.get("twitter") else None
    expert.email = form_data.get("email") or None
    expert.phone_number = form_data.get("phone_number") or None

    # Handle picture upload
    picture = request.files.get("picture")
    if picture:
        try:
            picture_url = upload_picture(picture)
            expert.picture_url = picture_url
        except Exception as e:
            print(e)
            status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
            return redirect(url_for("settings.create_company_view", _external=False, **status))

    # Handle price update
    price_str = form_data.get("price")
    if price_str and price_str.strip():
        try:
            price = float(price_str)
            if price < 0:
                return jsonify({"error": "Price cannot be negative"}), 400
            expert.price = price
        except ValueError:
            return jsonify({"error": "Invalid price format: must be a number"}), 400
    # Handle user assignment
    user_email = form_data.get("user_email")
    if user_email:
        user = User.query.filter_by(email=user_email).first()
        if not user:
            return jsonify({"error": "User with provided email does not exist"}), 400
        expert.user_id = user.id
    else:
        expert.user_id = None
