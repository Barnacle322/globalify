from flask import Blueprint, Response, jsonify, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    Chat,
    Message,
)
from ..schemas.message import ChatListSchema, ChatSchema, MessageSchema
from ..utils.enums import SenderType
from ..utils.gemini import func

message = Blueprint("message", __name__)


@message.route("/chat/create", methods=["POST"])
@login_required
def create_chat():
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    if current_user.id != user_id:
        return jsonify({"error": "Access denied"}), 403

    chat = Chat.get_by_user_id(user_id)
    if chat:
        return jsonify({"error": "Chat already exists"}), 400

    chat = Chat(user_id=user_id)
    db.session.add(chat)
    db.session.commit()

    return jsonify({"message": "Chat created successfully", "chat_id": chat.id})


@message.route("/chat/<int:chat_id>", methods=["POST"])
@login_required
def send_message(chat_id):
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    # Получаем или создаем чат
    chat = Chat.get_by_id(chat_id)
    if not chat:
        chat = Chat(user_id=current_user.id)
        db.session.add(chat)
        db.session.commit()

    # Создаем сообщение пользователя
    user_msg = Message(chat_id=chat.id, message=user_message, type=SenderType.USER)
    db.session.add(user_msg)
    db.session.commit()

    # Отправляем запрос в Gemini
    bot_response = func(user_message)

    # Обрабатываем ответ от Gemini
    bot_message_text = ""
    for res in bot_response:
        for candidate in res._result.candidates:
            for part in candidate.content.parts:
                bot_message_text += part.text + "\n"

    bot_message_text = bot_message_text.strip()

    # Создаем сообщение бота
    bot_msg = Message(chat_id=chat.id, message=bot_message_text, type=SenderType.GEMINI)
    db.session.add(bot_msg)
    db.session.commit()

    return jsonify({"user_message": user_message, "bot_message": bot_message_text})


@message.route("/chat/id/<int:chat_id>/", methods=["GET"])
@login_required
def get_chat(chat_id):
    chat = Chat.get_by_id(chat_id)
    if not chat:
        print("\n\n\n\n\n\n\n\n\n")
        print("Chat not found")
        return jsonify({"error": "Chat not found"}), 404

    messages = Message.get_by_chat_id(chat.id)

    if not messages:
        return jsonify({"error": "Messages not found"}), 404

    message_models = [MessageSchema.model_validate(msg) for msg in messages]
    chat_model = ChatSchema(id=chat.id, user_id=chat.user_id, created=chat.created, messages=message_models)

    return jsonify(chat_model.model_dump())


@message.route("/chats/<int:user_id>", methods=["GET"])
@login_required
def get_chats_by_user_id(user_id):
    if current_user.id != user_id:
        return jsonify({"error": "Access denied"}), 403

    chats = Chat.get_all_by_user_id(user_id)
    if not chats:
        return jsonify({"error": "Chats not found"}), 404

    chat_models = [ChatListSchema.model_validate(chat) for chat in chats]

    return jsonify([chat.model_dump() for chat in chat_models])


@message.route("/chat/<int:user_id>", methods=["GET"])
@login_required
def get_chat_by_user_id(user_id):
    if current_user.id != user_id:
        return jsonify({"error": "Access denied"}), 403

    chat = Chat.get_by_user_id(user_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    messages = Message.get_by_chat_id(chat.id)

    if not messages:
        return jsonify({"error": "Messages not found"}), 404

    message_models = [MessageSchema.model_validate(msg) for msg in messages]
    chat_model = ChatSchema(id=chat.id, user_id=chat.user_id, created=chat.created, messages=message_models)

    return jsonify(chat_model.model_dump())


@message.route("/stream/<prompt>")
@login_required
def streamed_response(prompt):
    def generate():
        response = func(prompt)
        for res in response:
            for candidate in res._result.candidates:
                for part in candidate.content.parts:
                    yield f"data: {part.text}\n\n".encode("utf-8")  # SSE

    return Response(generate(), content_type="text/event-stream")


# @message.route("/chat/<int:user_id>", methods=["POST"])
# def create_message(user_id: int):
#     data = request.get_json()

#     chat = Chat.get_by_user_id(user_id)
#     if not chat:
#         chat = Chat(user_id=user_id)
#         db.session.add(chat)
#         db.session.commit()

#     message = data.get("message")
#     type = data.get("type")

#     new_message = Message(chat_id=chat.id, message=message, type=type)
#     db.session.add(new_message)
#     db.session.commit()

#     return jsonify({"message": "Message created"}), 201
