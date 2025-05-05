import datetime

from flask import (
    Blueprint,
    jsonify,
    redirect,
    request,
    url_for,
)
from flask_login import current_user
from sqlalchemy.exc import IntegrityError

from ...extensions import db
from ...models.helpers import Industry
from ...models.superconnect import (
    # Event,
    Expert,
    Qualification,
    # TimeSlot,
)
from ...models.user import Company, Notification, User
from ...schemas.notification import NotificationItem, NotificationLayout
from ...utils.decorators import admin_only
from ...utils.enums import NotificationType, QualificationType
from ...utils.google_helpers.google_storage import upload_picture
from ...utils.scraper import add_https_prefix

superconnect = Blueprint("superconnect", __name__)


@superconnect.get("/")
@admin_only
def index():
    experts = Expert.get_all()

    return jsonify({"experts": experts})


@superconnect.get("/expert/create")
def create_expert():
    form_data = {
        "user_id": 1,
        "bio": "Experienced software engineer with a passion for AI.",
        "description": "I have over 10 years of experience in software development and specialize in machine learning and artificial intelligence.",
        "picture_url": "https://example.com/images/expert123.jpg",
        "industries": [1, 2, 3],
        "qualifications": [
            {
                "type": "CONTRACT",
                "title": "Senior Software Engineer",
                "start_date": "2018-01-01T00:00:00",
                "end_date": "2023-12-31T00:00:00",
                "qual_description": "Developed and maintained key features for a large-scale web application.",
                "company_name": "Acme Corp",
                "company_description": "A leading technology company.",
                "company_url": "https://acme.com",
            },
            {
                "type": "OFFICE",
                "title": "Master of Science in Computer Science",
                "start_date": "2016-09-01T00:00:00",
                "end_date": "2018-05-31T00:00:00",
                "qual_description": "Specialized in artificial intelligence and machine learning.",
                "company_id": None,
                "company_name": "University of Example",
                "company_description": None,
                "company_url": "https://example.edu",
                "set_as_current": True,
            },
        ],
    }
    try:
        if not form_data:
            return jsonify({"error": "No data provided"}), 400

        bio = form_data.get("bio")
        description = form_data.get("description")
        industry_ids = form_data.get("industries", [])
        qualifications_data = form_data.get("qualifications", [])
        user_id = form_data.get("user_id")
        if user_id:
            existing_expert = Expert.query.filter_by(user_id=current_user.id).first()
            if existing_expert:
                return jsonify({"error": "User is already an expert"}), 400
            user = User.get_by_id(user_id)

        industries = []
        if industry_ids:
            industries = Industry.query.filter(Industry.id.in_(industry_ids)).all()
            if len(industries) != len(industry_ids):
                return jsonify({"error": "Some industries not found"}), 404
            elif len(industries) > 5:  # mb industries limit for experts ####################
                return jsonify({"error": "Expert can't have more thatn 5 industries"}), 404
        else:
            industries = []

        if picture := request.files.get("picture"):
            try:
                picture_url = upload_picture(picture)
            except Exception as e:
                print(e)
                return jsonify({"error": "Picture uploading error"}), 400

        expert = Expert(
            user_id=user_id if user_id else None,
            user=user if user else None,
            bio=bio,
            industries=industries,
            description=description,
            picture_url=picture_url,
        )

        qualifications: list[Qualification] = []
        for qual_data in qualifications_data:
            qual_type = qual_data.get("type")
            title = qual_data.get("title")
            description = qual_data.get("qual_description")
            company_id = qual_data.get("company_id")
            company = Company.get_by_id(company_id) if company_id else None
            if company:
                company_name = company.name
                company_description = company.description
                company_url = "globalify.xyz/company/" + company.slug
            else:
                company_name = qual_data.get("company_name")
                company_description = qual_data.get("company_description")
                company_url = qual_data.get("company_url")
                if company_url:
                    company_url = add_https_prefix(company_url)
            start_date_str = qual_data.get("start_date")
            end_date_str = qual_data.get("end_date")
            start_date = datetime.datetime.fromisoformat(start_date_str) if start_date_str else None
            end_date = datetime.datetime.fromisoformat(end_date_str) if end_date_str else None
            if start_date and end_date and end_date < start_date:
                return jsonify({"error": "Validation error: end_date cannot be before start_date"}), 400
            set_as_current = qual_data.get("set_as_current", False)

            if not (qual_type or title or company_name):
                return jsonify({"error": "Qualification type, title, employment name are required"}), 400

            if qual_type not in QualificationType.__members__:
                return jsonify({"error": f"Invalid qualification type: {qual_type}"}), 400

            qualification = Qualification(
                type=QualificationType[qual_type],
                title=title,
                description=description,
                company_id=company_id,
                company_name=company_name,
                company_description=company_description,
                company_url=company_url,
                start_date=start_date,
                end_date=end_date,
            )
            qualifications.append(qualification)

            if set_as_current and (qual_type != QualificationType.EDUCATION):
                db.session.add(qualification)
                db.session.flush()
                expert.current_position_id = qualification.id

        expert.qualifications = qualifications

        db.session.add(expert)
        db.session.commit()

        if expert and user:
            notification = Notification(
                user=user,
                json_data=NotificationLayout(
                    title="You are expert now!",
                    msg="Click here to view your expert page.",
                    type="system",
                    item=NotificationItem(
                        url=url_for("superconnect.get_expert", expert_id=user_id, _external=True),
                        type=NotificationType.INFO.value,
                    ),
                ).model_dump(),
            )
            db.session.add(notification)

        expert_data = {
            "id": expert.id,
            "user_id": expert.user_id,
            "bio": expert.bio,
            "description": expert.description,
            "picture_url": expert.picture_url,
            "current_position_id": expert.current_position_id,
            "qualifications": [
                {
                    "id": q.id,
                    "type": q.type.value,
                    "title": q.title,
                    "description": q.description,
                    "company_id": q.company_id,
                    "company_name": q.company_name,
                    "company_description": q.company_description,
                    "company_url": q.company_url,
                    "start_date": q.start_date.isoformat() if q.start_date else None,
                    "end_date": q.end_date.isoformat() if q.end_date else None,
                }
                for q in expert.qualifications
            ],
            "industries": [i.id for i in expert.industries],
        }

        return jsonify({"expert": expert_data}), 200

    except IntegrityError as e:
        print(f"Database error: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Failed to create expert: {str(e)}"}), 500
    except Exception as e:
        print(f"Failed to create expert: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Failed to create expert: {str(e)}"}), 500


# @superconnect.post("/superconnect/", methods=["POST"])
# @login_required
# @check_user_info_complete
# @check_verification
# def book_event():
#     try:
#         form_data = request.get_json()
#         expert_id = form_data.get("expert_id")
#         event_info = form_data.get("event_info")

#         expert = Expert.get_by_id(expert_id)

#         if not event_info:
#             return jsonify({"error": "Empty event info"}), 400
#         if not expert:
#             return jsonify({"error": "Expert not found"}), 404

#         now = datetime.datetime.now(datetime.UTC)
#         minimum_notice_time = now + datetime.timedelta(minutes=expert.minimum_notice_minutes)

#         if event_info.start_time < minimum_notice_time:
#             return jsonify({"error": "Minimum notice period Error"}), 400

#         db.session.commit()

#         return jsonify({}), 200

#     except Exception as e:
#         db.session.rollback()
#         return jsonify({"error": f"Failed to book event: {str(e)}"}), 500
