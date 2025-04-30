import datetime

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Company, User
from ..models.helpers import Industry
from ..models.superconnect import (
    EventStatus,
    # TimeSlot,
    # Event,
    Expert,
    Qualification,
    SessionRequest,
)
from ..schemas.superconnect import ExpertSchema, QualificationSchema, SessionSchema
from ..utils.decorators import check_user_info_complete, check_verification
from ..utils.enums import QualificationType, Status, StatusType
from ..utils.errors.error_messages import PICTURE_NOT_LOADED
from ..utils.google_helpers.google_storage import delete_blob_from_url, upload_picture
from ..utils.scraper import add_https_prefix

superconnect = Blueprint("superconnect", __name__)


@superconnect.route("/list")
def index():
    experts = Expert.get_all()
    return render_template("superconnect/index.html", experts=experts)


@superconnect.get("/superconnect/expert/<expert_id>")
@login_required
@check_user_info_complete
@check_verification
def get_expert(expert_id):
    expert = Expert.get_by_id(expert_id)

    if not expert:
        return redirect(url_for("superconnect.index"))

    # return jsonify({"expert": expert})
    return render_template("superconnect/expert.html", expert=expert)


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

    if picture := request.files.get("picture"):
        try:
            picture_url = upload_picture(picture)
            if expert.picture_url:
                try:
                    delete_blob_from_url(expert.picture_url)
                except Exception as e:
                    print(e)
            expert.picture_url = picture_url
        except Exception as e:
            print(e)
            status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
            return redirect(url_for("settings.index", _external=False, **status))

    # industry_ids = form_data.get("industries", [])
    # if industry_ids:
    #     industries = Industry.query.filter(Industry.id.in_(industry_ids)).all()
    #     if len(industries) != len(industry_ids):
    #         return jsonify({"error": "Some industries not found"}), 404

    #     elif len(industries) > 5:  # mb industries limit for experts ####################
    #         return jsonify({"error": "Expert can't have more thatn 5 industries"}), 404

    #     expert.industries = industries
    # else:
    #     expert.industries = []

    qualifications: list[Qualification] = []
    for qual_data in qualifications_data:
        qual_type = qual_data.get("type")
        title = qual_data.get("title")
        description = qual_data.get("qual_description")
        company_id = qual_data.get("company_id")
        company = Company.get_by_id(company_id) if company_id else None
        if company:
            company_name = company.name  # mb need logic for company approvement of globalify's company qualification
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
            return jsonify({"error": "Validation error: end date cannot be before start date"}), 400
        set_as_current = qual_data.get("set_as_current", False)

        if not (qual_type and title or company_name):
            return jsonify({"error": "Qualification type, title, employment name are required"}), 400

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
        # "industries": [i.id for i in expert.industries],
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


@superconnect.get("/expert/<expert_id>")
def get_expert_by_id(expert_id):
    expert = Expert.get_by_id(expert_id)
    if not expert:
        return jsonify({"error": "Expert not found"}), 404

    # Сериализация данных через Pydantic-схему
    expert_data = ExpertSchema(
        id=expert.id,
        name=expert.user.user_info.full_name,
        user_id=expert.user_id,
        bio=expert.bio,
        description=expert.description,
        picture_url=expert.picture_url,
        current_position_id=expert.current_position_id,
        qualifications=[
            QualificationSchema(
                id=q.id,
                type=q.type.value,
                title=q.title,
                description=q.description,
                company_id=q.company_id if q.company_id else None,
                company_name=q.company_name,
                company_description=q.company_description,
                company_url=q.company_url,
                start_date=q.start_date,
                end_date=q.end_date,
            )
            for q in expert.qualifications
        ],
    )

    # Преобразование Pydantic-объекта в словарь
    return jsonify({"expert": expert_data.model_dump()})


@superconnect.post("/book-session/<expert_id>")
def book_session(expert_id):
    expert = Expert.get_by_id(expert_id)
    if not expert:
        return jsonify({"error": "Expert not found"}), 404

    existing_request = SessionRequest.get_existing_by_user_id(expert_id)
    if existing_request:
        return jsonify({"error": "You have already requested a session with this expert"}), 400
    print("Booking session with expert ID:", expert_id)
    try:
        session_request = SessionRequest(expert_id=expert_id, user_id=current_user.id)
        db.session.add(session_request)
        db.session.commit()
    except Exception as e:
        print("Error while creating session request:", e)

    return jsonify({"message": "Session request sent successfully!"}), 200


@superconnect.get("/sessions/")
def get_user_sessions():
    user = User.get_by_id(1)
    if not user:
        return jsonify({"error": "Expert not found"}), 404

    session_requests = SessionRequest.get_all_by_user_id(1)
    return render_template("superconnect/sessions.html", session_requests=session_requests)
    # return jsonify("superconnect/sessions.html", session_requests=session_requests)


@superconnect.get("/get_sessions/")
def user_sessions():
    print(current_user.id)
    session_requests = SessionRequest.get_all_by_user_id(current_user.id)

    if session_requests is None:
        return jsonify({"sessions": []})

    session_list = []
    for s_request in session_requests:
        session_data = SessionSchema(
            id=s_request.id,
            expert_name="s_request.expert.user.user_info.full_name",
            picture_url=s_request.expert.picture_url or "",
            status=s_request.status.value,
            created_at=s_request.created_at.date(),
        )
        session_list.append(session_data.model_dump())

    return jsonify({"sessions": session_list})
