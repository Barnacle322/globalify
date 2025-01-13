from datetime import datetime

from flask import (
    Blueprint,
    jsonify,
    request,
)
from flask_login import login_required

from ..extensions import db
from ..models import (
    Chat,
    Message,
)

message = Blueprint("message", __name__)


@message.route("/chat/<int:user_id>", methods=["POST"])
def create_message(user_id: int):
    data = request.get_json()

    chat = Chat.get_by_user_id(user_id)
    if not chat:
        chat = Chat(user_id=user_id)
        db.session.add(chat)
        db.session.commit()

    message = data.get("message")
    type = data.get("type")

    new_message = Message(chat_id=chat.id, message=message, type=type)
    db.session.add(new_message)
    db.session.commit()

    return jsonify({"message": "Message created"}), 201
