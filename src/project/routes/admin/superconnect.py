import datetime

from flask import (
    Blueprint,
    jsonify,
    request,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from src.project.models.helpers import Industry
from src.project.models.user import User
from src.project.utils.enums import QualificationType

from ...extensions import db
from ...models.superconnect import (
    # Event,
    Expert,
    Qualification,
    # TimeSlot,
)
from ...utils.decorators import check_user_info_complete, check_verification

superconnect = Blueprint("superconnect", __name__)


@superconnect.get("admin/superconnect/")
@login_required
@check_user_info_complete
@check_verification
def index():
    experts = Expert.get_all()

    return jsonify({"experts": experts})


@superconnect.get("admin/superconnect/expert/create")
@login_required
@check_user_info_complete
@check_verification
def create_expert():
    try:
        form_data = request.get_json()
        if not form_data:
            return jsonify({"error": "No data provided"}), 400

        bio = form_data.get("bio")
        description = form_data.get("description")
        picture_url = form_data.get("picture_url")
        current_position_id = form_data.get("current_position_id")
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

        expert = Expert(
            user_id=user_id if user_id else None,
            user=user if user else None,
            bio=bio,
            description=description,
            picture_url=picture_url,
            current_position_id=current_position_id,
        )

        qualifications: list[Qualification] = []
        for qual_data in qualifications_data:
            qual_type = qual_data.get("type")
            title = qual_data.get("title")
            description = qual_data.get("description")
            company_id = qual_data.get("company_id")
            company_name = qual_data.get("company_name")
            company_description = qual_data.get("company_description")
            company_url = qual_data.get("company_url")
            start_date = qual_data.get("start_date")
            end_date = qual_data.get("end_date")

            if not (qual_type and title):
                return jsonify({"error": "Qualification type and title are required"}), 400

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

        expert.qualifications = qualifications

        db.session.add(expert)
        db.session.commit()

        # Формирование ответа
        expert_data = {
            "id": expert.id,
            "user_id": expert.user_id,
            "bio": expert.bio,
            "description": expert.description,
            "picture_url": expert.picture_url,
            "current_position_id": expert.current_position_id,
            "created_at": expert.created_at.isoformat(),  # type: ignore
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
