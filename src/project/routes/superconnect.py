import datetime

from flask import (
    Blueprint,
    jsonify,
    request,
)
from flask_login import login_required

from ..extensions import db
from ..models.superconnect import (
    # Event,
    Expert,
    Qualification,
    # TimeSlot,
)
from ..utils.decorators import check_user_info_complete, check_verification

superconnect = Blueprint("superconnect", __name__)


@superconnect.get("/superconnect/")
@login_required
@check_user_info_complete
@check_verification
def index():
    experts = Expert.get_all()

    return jsonify({"experts": experts})


@superconnect.get("/superconnect/expert/<expert_id>}")
@login_required
@check_user_info_complete
@check_verification
def get_expert(expert_id):
    expert = Expert.get_by_id(expert_id)

    return jsonify({"expert": expert})


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
