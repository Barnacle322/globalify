from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
)

from ..extensions import db
from ..models import User
from ..models.superconnect import (
    Expert,
    Qualification,
    SessionRequest,
)
from ..schemas.superconnect import ExpertSchema, QualificationSchema

superconnect = Blueprint("superconnect", __name__)


@superconnect.route("/api/experts")
def api_experts():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 9, type=int)

    expertise = request.args.get("expertise", "All")
    region = request.args.get("region", "Worldwide")
    search_query = request.args.get("search", "")

    query = Expert.query

    if expertise != "All":
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
            "current_position_id": expert.current_position_id,
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


@superconnect.route("/list", methods=["GET"])
def index():
    return render_template("superconnect/index.html")


@superconnect.get("/expert/<expert_id>")
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
        current_position_id=expert.current_position_id,
        qualifications=[
            QualificationSchema(
                id=q.id,
                type=q.type.value,
                title=q.title,
                description=q.description,
                company_id=q.company_id,
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

    existing_request = SessionRequest.get_existing_by_expert_id(expert_id=expert_id)
    if existing_request:
        return jsonify({"error": "You have already requested a session with this expert"}), 400
    print("Booking session with expert ID:", expert_id)
    try:
        session_request = SessionRequest(expert_id=expert_id)
        db.session.add(session_request)
        db.session.commit()
    except Exception as e:
        print("Error while creating session request:", e)

    return jsonify({"message": "Session request sent successfully!"}), 200
