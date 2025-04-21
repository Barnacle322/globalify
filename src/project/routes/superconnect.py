import datetime

from flask import (
    Blueprint,
    jsonify,
    redirect,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Company, User
from ..models.helpers import Industry
from ..models.superconnect import (
    # Event,
    Expert,
    Qualification,
    # TimeSlot,
)
from ..utils.decorators import check_user_info_complete, check_verification
from ..utils.enums import QualificationType

superconnect = Blueprint("superconnect", __name__)


@superconnect.get("/superconnect/")
@login_required
@check_user_info_complete
@check_verification
def index():
    experts = Expert.get_all()

    return jsonify({"experts": experts})


@superconnect.get("/superconnect/expert/<expert_id>")
@login_required
@check_user_info_complete
@check_verification
def get_expert(expert_id):
    expert = Expert.get_by_id(expert_id)

    return jsonify({"expert": expert})


@superconnect.get("/superconnect/request/")
@login_required
@check_user_info_complete
@check_verification
def expert_request():
    form_data = request.get_json()
    if not form_data:
        return jsonify({"error": "No data provided"}), 400
    call_time = form_data.get(
        "call_time",
    )
    user = User.get_by_id(current_user.id)

    return jsonify({"user": user, "call_time": call_time})


@superconnect.post("/superconnect/expert/update/")
@login_required
@check_user_info_complete
@check_verification
def update_expert():
    expert = Expert.get_by_id(current_user.id)

    if not expert:
        print("Expert profile not found")
        return redirect(url_for("payment.pricing"))  # mb another redirect

    form_data = request.get_json()
    if not form_data:
        return jsonify({"error": "No data provided"}), 400

    industry_ids = form_data.get("industries", [])
    qualifications_data = form_data.get("qualifications", [])

    expert.bio = form_data.get("bio", expert.bio)
    expert.picture_url = form_data.get("picture_url", expert.picture_url)

    industry_ids = form_data.get("industries", [])
    if industry_ids:
        industries = Industry.query.filter(Industry.id.in_(industry_ids)).all()
        if len(industries) != len(industry_ids):
            return jsonify({"error": "Some industries not found"}), 404
        expert.industries = industries
    else:
        expert.industries = []

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
        start_date_str = qual_data.get("start_date")
        end_date_str = qual_data.get("end_date")
        start_date = datetime.datetime.fromisoformat(start_date_str) if start_date_str else None
        end_date = datetime.datetime.fromisoformat(end_date_str) if end_date_str else None
        if start_date and end_date and end_date < start_date:
            return jsonify({"error": "Validation error: end_date cannot be before start_date"}), 400
        set_as_current = qual_data.get("set_as_current", False)

        if not (qual_type and title):
            return jsonify({"error": "Qualification type and title are required"}), 400

        if qual_type not in QualificationType.__members__:
            return jsonify({"error": f"Invalid qualification type: {qual_type}"}), 400

        qualification = Qualification(
            type=QualificationType[qual_type],
            title=title,
            description=description,
            company_id=company_id if company_id else None,
            company_name=company_name,
            company_description=company_description,
            company_url=company_url,
            start_date=start_date,
            end_date=end_date,
        )
        qualifications.append(qualification)

        if set_as_current and (qual_type != QualificationType.EDUCATION):
            db.session.add(qualification)  # To put selected qualification to current job or whatever
            db.session.flush()
            expert.current_position_id = qualification.id

    expert.qualifications = qualifications

    db.session.commit()

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

    return jsonify({"expert": expert_data})


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
