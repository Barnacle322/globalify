from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
)
from flask_login import current_user

from ..extensions import db
from ..models import User
from ..models.superconnect import (
    Expert,
    Qualification,
    QualificationType,
    SessionRequest,
    SessionStatus,
)
from ..schemas.superconnect import ExpertSchema, QualificationSchema, SessionSchema
from ..utils.decorators import (
    check_user_info_complete,
    check_verification,
)

superconnect = Blueprint("superconnect", __name__)


@superconnect.route("/api/experts")
@check_user_info_complete
@check_verification
def api_experts():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 9, type=int)

    expertise = request.args.get("expertise", "All")
    print("Agahan", expertise)
    region = request.args.get("region", "Worldwide")
    search_query = request.args.get("search", "")

    query = Expert.query

    if expertise != "All":
        print("Agahan2", expertise)
        query = query.join(Expert.qualifications).filter(Qualification.type == expertise)

    if region != "Worldwide":
        query = query.join(Expert.user).join(User.user_info).filter(User.user_info.country == region)

    if search_query:
        from ..models import UserInfo

        query = (
            query.join(Expert.user)
            .join(User.user_info)
            .filter(
                db.or_(
                    UserInfo.first_name.ilike(f"%{search_query}%"),
                    UserInfo.last_name.ilike(f"%{search_query}%"),
                    Expert.bio.ilike(f"%{search_query}%"),
                )
            )
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    experts_data = []
    for expert in pagination.items:
        expert_data = {
            "id": expert.id,
            "name": f"{expert.first_name} {expert.last_name}",
            "picture_url": expert.picture_url,
            "bio": expert.bio or "This expert helps businesses expand globally.",
            "position": expert.position,
            "experience_years": len(expert.qualifications) if expert.qualifications else 0,
            "qualifications": [{"id": q.id, "type": q.type.value, "title": q.title} for q in expert.qualifications][:3],
        }
        experts_data.append(expert_data)

    pagination_meta = {
        "page": page,
        "per_page": per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_num": pagination.next_num if pagination.has_next else None,
        "prev_num": pagination.prev_num if pagination.has_prev else None,
    }

    return jsonify(
        {
            "experts": experts_data,
            "pagination": pagination_meta,
            "filters": {"expertise": expertise, "region": region, "search": search_query},
        }
    )


@superconnect.route("/api/qualification-types", methods=["GET"])
@check_user_info_complete
@check_verification
def get_qualification_types():
    types = [{"value": typ.name, "name": typ.value.capitalize()} for typ in QualificationType]

    return jsonify({"qualification_types": types})


@superconnect.route("/list", methods=["GET"])
@check_user_info_complete
@check_verification
def index():
    return render_template("superconnect/index.html", current_user=current_user)


@superconnect.get("/get/<expert_id>")
@check_user_info_complete
@check_verification
def get_expert_by_id(expert_id):
    expert = Expert.get_by_id(expert_id)
    if not expert:
        return jsonify({"error": "Expert not found"}), 404

    # Сериализация данных через Pydantic-схему
    expert_data = ExpertSchema(
        id=expert.id,
        name=expert.full_name,
        user_id=expert.user_id,
        bio=expert.bio,
        description=expert.description,
        picture_url=expert.picture_url,
        position=expert.position,
        linkedin=expert.linkedin,
        twitter=expert.twitter,
        email=expert.email,
        phone_number=expert.phone_number,
        location=expert.location,
        price=expert.price,
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
@check_user_info_complete
@check_verification
def book_session(expert_id):
    # Получаем данные из JSON запроса
    request_data = request.get_json()
    notes = request_data.get("notes", "") if request_data else ""

    expert = Expert.get_by_id(expert_id)
    if not expert:
        return jsonify({"error": "Expert not found"}), 404

    # existing_request = SessionRequest.get_existing_by_user_id(expert_id)
    # if existing_request:
    #     return jsonify({"error": "You have already requested a session with this expert"}), 400

    print("Booking session with expert ID:", expert_id)
    try:
        # Создаем запрос на сессию с полем notes
        session_request = SessionRequest(expert_id=expert_id, user_id=current_user.id, notes=notes)
        db.session.add(session_request)
        db.session.commit()
    except Exception as e:
        print("Error while creating session request:", e)
        db.session.rollback()
        return jsonify({"error": f"Failed to create session request: {str(e)}"}), 500

    return jsonify({"message": "Session request sent successfully!", "redirect_url": "/expert/sessions/"}), 200


@superconnect.get("/sessions/")
@check_user_info_complete
@check_verification
def get_user_sessions():
    return render_template("superconnect/sessions.html", current_user=current_user)


@superconnect.get("/get_sessions/")
@check_user_info_complete
@check_verification
def user_sessions():
    print(current_user.id)
    user = User.get_by_id(current_user.id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not user.is_expert:
        print("User is a client")
        session_requests = SessionRequest.get_all_by_user_id(current_user.id)
    else:
        print("User is an expert")
        expert = Expert.get_by_user_id(current_user.id)
        if not expert:
            return jsonify({"error": "Expert not found"}), 404
        session_requests = SessionRequest.get_all_by_expert_id(expert.id)

    if session_requests is None:
        return jsonify({"sessions": []})

    session_list = []
    for s_request in session_requests:
        session_data = SessionSchema(
            id=s_request.id,
            expert_name=s_request.expert.full_name,
            expert_email=s_request.expert.email or "",
            user_name=s_request.user.user_info.full_name,
            user_email=s_request.user.email or "",
            expert_picture_url=s_request.expert.picture_url or "",
            user_picture_url=s_request.user.user_info.picture_url or "",
            notes=s_request.notes or "",
            type=s_request.type.value,
            status=s_request.status.value,
            created_at=s_request.created_at.date(),
        )
        session_list.append(session_data.model_dump())

    return jsonify({"sessions": session_list})


@superconnect.post("/session/action/")
@check_user_info_complete
@check_verification
def change_session_status():
    form_data = request.get_json()
    if not form_data:
        return jsonify({"error": "No data provided"}), 400

    session_id = form_data.get("session_id")
    session = SessionRequest.get_by_id(session_id)

    if not session:
        return jsonify({"error": "Session not found"}), 404

    action = form_data.get("action")

    action_map = {
        "cancel": SessionStatus.CANCELED,
        "delete": SessionStatus.DELETED,
        "past": SessionStatus.PAST,
        "upcoming": SessionStatus.UPCOMING,
    }

    new_status = action_map.get(action)

    if new_status is None:
        return jsonify({"error": "Invalid action"}), 400

    session.status = new_status
    db.session.commit()

    return jsonify({"message": "Session status updated successfully"}), 200
