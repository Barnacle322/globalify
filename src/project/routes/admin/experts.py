import datetime

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from slugify import slugify
from sqlalchemy import delete

from ...extensions import db
from ...models.superconnect import (
    Expert,
    Qualification,
)
from ...models.user import Company, User
from ...utils.decorators import admin_only
from ...utils.enums import QualificationType, Status, StatusType
from ...utils.errors.error_messages import PICTURE_NOT_LOADED
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
def update_expert_view(id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    expert = Expert.get_by_id(id)
    if not expert:
        status = Status(StatusType.ERROR, "Expert not found.").get_status()
        return redirect(url_for("admin.expert.index", _external=True, **status))

    qualification_types = [qt.value for qt in QualificationType]

    return render_template(
        "admin/experts/update_expert.html",
        expert=expert,
        qualificationTypes=qualification_types,
        status_type=status_type,
        msg=msg,
    )


@expert.get("/qualifications/<int:id>")
@admin_only
def get_expert_qualifications(id):
    qualifications = Qualification.get_all_by_expert_id(id)

    if qualifications:
        json_qualifications = [
            {
                "id": q.id,
                "type": q.type.value,
                "title": q.title,
                "start_date": q.start_date.isoformat() if q.start_date else None,
                "end_date": q.end_date.isoformat() if q.end_date else None,
                "description": q.description,
                "company_name": q.company_name,
                "company_url": q.company_url,
            }
            for q in qualifications
        ]
    else:
        json_qualifications = []

    return jsonify(json_qualifications), 200


@expert.route("/create", methods=["GET", "POST"])
@admin_only
def create_expert():
    if request.method == "GET":
        status_type, msg = None, None
        if query := request.args:
            status_type = query.get("type")
            msg = query.get("msg")

        qualification_types = [qt.value for qt in QualificationType]

        return render_template(
            "admin/experts/create_expert.html",
            qualificationTypes=qualification_types,
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
                return redirect(url_for("admin.experts.create_expert", _external=True, **status))

        price = None
        if price_str and price_str.strip():  # Check if non-empty and non-whitespace
            try:
                price = float(price_str)
                if price < 0:
                    return jsonify({"error": "Price cannot be negative"}), 400
            except Exception as e:
                print(e)
                status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
                return redirect(url_for("admin.experts.create_expert", _external=True, **status))

        first_name = form_data.get("first_name") or None
        last_name = form_data.get("last_name") or None
        if first_name is None or last_name is None:
            return jsonify({"error": "First name and last name are required"}), 400

        expert = Expert(
            first_name=first_name,
            last_name=last_name,
            firm_name=form_data.get("firm_name") or None,
            slug=slugify(f"{first_name} {last_name}"),
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
        )

        db.session.add(expert)
        db.session.flush()

        qualifications_data = form_data.get("qualifications", [])
        if qualifications_data:
            for qual_data in qualifications_data:
                qual_type = qual_data.get("type")
                title = qual_data.get("title")
                description = qual_data.get("description")
                company_id = qual_data.get("company_id")
                company = Company.get_by_id(company_id) if company_id else None
                if company:
                    company_name = company.name
                    company_description = company.description
                    company_url = "globalify.xyz/company/" + company.slug
                else:
                    company_name = qual_data.get("company_name")
                    company_description = qual_data.get("company_description")
                    company_url = qual_data.get("company_url") or None
                    if company_url:
                        company_url = add_https_prefix(company_url)
                start_date_str = qual_data.get("start_date")
                end_date_str = qual_data.get("end_date")
                start_date = datetime.datetime.fromisoformat(start_date_str) if start_date_str else None
                end_date = datetime.datetime.fromisoformat(end_date_str) if end_date_str else None
                if start_date and end_date and end_date < start_date:
                    return jsonify({"error": "Validation error: end_date cannot be before start_date"}), 400

                if not qual_type or not title or not company_name:
                    return jsonify({"error": "Qualification type, title, and company name are required"}), 400

                if qual_type not in [qt.value for qt in QualificationType]:
                    return jsonify({"error": f"Invalid qualification type: {qual_type}"}), 400

                qualification = Qualification(
                    expert_id=expert.id,
                    type=QualificationType(qual_type),
                    title=title,
                    description=description,
                    company_id=company_id,
                    company_name=company_name,
                    company_description=company_description,
                    company_url=company_url,
                    start_date=start_date,
                    end_date=end_date,
                )
                db.session.add(qualification)

        try:
            db.session.commit()
        except Exception as e:
            print(f"Error: {e}")
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("admin.experts.create_expert", _external=True, **status))

        status = Status(StatusType.SUCCESS, "Expert created successfully!").get_status()
        return redirect(url_for("admin.experts.index", _external=True, **status))


@expert.post("/update/<int:id>")
@admin_only
def update_expert(id):
    form_data = request.get_json()
    if not form_data:
        print("No data provided")
        return jsonify({"error": "No data provided"}), 400

    expert = Expert.get_by_id(id)
    if not expert:
        print("Expert not found")
        return jsonify({"error": "Expert not found"}), 404

    try:
        if not expert.first_name or not expert.last_name:
            print("First name and last name are required")
            return jsonify({"error": "First name and last name are required"}), 400
        expert.first_name = form_data.get("first_name")
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

        price_str = form_data.get("price")
        if price_str and price_str.strip():
            try:
                price = float(price_str)
                if price < 0:
                    return jsonify({"error": "Price cannot be negative"}), 400
                expert.price = price
            except ValueError:
                return jsonify({"error": "Invalid price format: must be a number"}), 400

        user_email = form_data.get("user_email")
        if user_email:
            user = User.query.filter_by(email=user_email).first()
            if not user:
                print("User with provided email does not exist")
                return jsonify({"error": "User with provided email does not exist"}), 400
            expert.user_id = user.id
        else:
            expert.user_id = None

        picture = request.files.get("picture")
        if picture:
            try:
                picture_url = upload_picture(picture)
                expert.picture_url = picture_url
            except Exception as e:
                print(e)
                status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
                return redirect(url_for("admin.experts.update_expert", _external=True, **status))

        qualifications_data = form_data.get("qualifications", [])
        deleted_ids = form_data.get("deleted_qualifications", [])

        if deleted_ids:
            Qualification.delete_by_id_list(deleted_ids)

        for qual_data in qualifications_data:
            qual_id = qual_data.get("id")
            qual_type = qual_data.get("type")
            title = qual_data.get("title")
            description = qual_data.get("description")
            company_id = qual_data.get("company_id")
            company_name = qual_data.get("company_name")
            company_description = qual_data.get("company_description")
            company_url = qual_data.get("company_url")
            start_date_str = qual_data.get("start_date")
            end_date_str = qual_data.get("end_date")

            start_date = datetime.datetime.fromisoformat(start_date_str) if start_date_str else None
            end_date = datetime.datetime.fromisoformat(end_date_str) if end_date_str else None

            if start_date and end_date and end_date < start_date:
                print("Validation error: end_date cannot be before start_date")
                return jsonify({"error": "Validation error: end_date cannot be before start_date"}), 400

            if not qual_type or not title or not company_name:
                print("Qualification type, title, and company name are required")
                return jsonify({"error": "Qualification type, title, and company name are required"}), 400

            if qual_type not in [qt.value for qt in QualificationType]:
                print(f"Invalid qualification type: {qual_type}")
                return jsonify({"error": f"Invalid qualification type: {qual_type}"}), 400

            if qual_id:
                qualification = Qualification.get_by_id(qual_id)
                if not qualification:
                    continue

                qualification.type = QualificationType(qual_type)
                qualification.title = title
                qualification.description = description
                qualification.company_id = company_id
                qualification.company_name = company_name
                qualification.company_description = company_description
                qualification.company_url = add_https_prefix(company_url) if company_url else None
                qualification.start_date = start_date
                qualification.end_date = end_date
                db.session.add(qualification)
            else:
                company = Company.get_by_id(company_id) if company_id else None
                if company:
                    company_name = company.name
                    company_description = company.description
                    company_url = "globalify.xyz/company/" + company.slug
                else:
                    company_url = add_https_prefix(company_url) if company_url else None

                qualification = Qualification(
                    expert_id=expert.id,
                    type=QualificationType(qual_type),
                    title=title,
                    description=description,
                    company_id=company_id,
                    company_name=company_name,
                    company_description=company_description,
                    company_url=company_url,
                    start_date=start_date,
                    end_date=end_date,
                )
                db.session.add(qualification)

        db.session.commit()
        status = Status(StatusType.SUCCESS, "Expert updated successfully!").get_status()
        return redirect(url_for("admin.experts.index", _external=True, **status))

    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("admin.experts.update_expert", id=id, _external=True, **status))
