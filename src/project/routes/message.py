from flask import Blueprint, Response, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import delete

from ..extensions import db
from ..models import (
    Chat,
    Message,
)
from ..schemas.message import ChatListSchema, ChatSchema, MessageSchema
from ..utils.decorators import check_verification, check_user_info_complete
from ..utils.enums import SenderType
from ..utils.gemini import create_summary, generate_response

message = Blueprint("message", __name__)


@message.route("/chat/<int:chat_id>", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def send_message(chat_id):
    data = request.get_json()
    user_message = data.get("message", "").strip()
    print(chat_id)

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    chat = Chat.get_by_id(chat_id)

    if not chat:
        chat = Chat(user_id=current_user.id)
        db.session.add(chat)
        db.session.commit()

    if chat.name == "New chat":
        chat.name = user_message[:30]

    user_msg = Message(chat_id=chat.id, message=user_message, type=SenderType.USER)
    db.session.add(user_msg)
    db.session.commit()

    messages = Message.get_by_chat_id(chat.id)

    old_messages = [
        {"role": "user" if msg.type == SenderType.USER else "assistant", "parts": [msg.message]} for msg in messages
    ]

    old_messages.append({"role": "user", "parts": [user_message]})

    bot_response = generate_response(user_message, old_messages)
    summary_bot_summary = create_summary(user_message)

    bot_summary_text = ""
    for res in summary_bot_summary:
        for candidate in res._result.candidates:
            for part in candidate.content.parts:
                bot_summary_text += part.text

    bot_summary_text = bot_summary_text.strip()

    chat.name = bot_summary_text
    db.session.commit()

    bot_message_text = ""
    for res in bot_response:
        for candidate in res._result.candidates:
            for part in candidate.content.parts:
                bot_message_text += part.text

    bot_message_text = bot_message_text.strip()
    print(bot_message_text)

    bot_msg = Message(chat_id=chat.id, message=bot_message_text, type=SenderType.GEMINI)
    db.session.add(bot_msg)
    db.session.commit()

    return jsonify({"user_message": user_message, "bot_message": bot_message_text, "chat_id": chat.id})


@message.route("/chat", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def send_message_with_create_chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    chat = Chat(user_id=current_user.id)
    db.session.add(chat)
    db.session.commit()

    user_msg = Message(chat_id=chat.id, message=user_message, type=SenderType.USER)
    db.session.add(user_msg)
    db.session.commit()

    messages = Message.get_by_chat_id(chat.id)

    old_messages = [
        {"role": "user" if msg.type == SenderType.USER else "assistant", "parts": [msg.message]} for msg in messages
    ]

    old_messages.append({"role": "user", "parts": [user_message]})

    bot_response = generate_response(user_message, old_messages)
    summary_bot_summary = create_summary(user_message)

    bot_summary_text = ""
    for res in summary_bot_summary:
        for candidate in res._result.candidates:
            for part in candidate.content.parts:
                bot_summary_text += part.text

    bot_summary_text = bot_summary_text.strip()

    chat.name = bot_summary_text
    db.session.commit()

    bot_message_text = ""
    for res in bot_response:
        for candidate in res._result.candidates:
            for part in candidate.content.parts:
                bot_message_text += part.text

    bot_message_text = bot_message_text.strip()

    bot_msg = Message(chat_id=chat.id, message=bot_message_text, type=SenderType.GEMINI)
    db.session.add(bot_msg)
    db.session.commit()

    serialized_chat = ChatSchema(
        id=chat.id, user_id=chat.user_id, created=chat.created, name=chat.name, messages=None
    ).model_dump_json()

    return jsonify(
        {
            "user_message": user_message,
            "bot_message": bot_message_text,
            "bot_summary_text": bot_summary_text,
            "chat": serialized_chat,
        }
    )


@message.route("/chat/id/<int:chat_id>/", methods=["GET"])
@login_required
@check_verification
@check_user_info_complete
def get_chat(chat_id):
    chat = Chat.get_by_id(chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    messages = Message.get_by_chat_id(chat.id)
    if not messages:
        message_models = []
    else:
        message_models = [MessageSchema.model_validate(msg) for msg in messages]
    chat_model = ChatSchema(
        id=chat.id, user_id=chat.user_id, name=chat.name, created=chat.created, messages=message_models
    )

    return jsonify(chat_model.model_dump())


@message.route("/chats/<int:user_id>", methods=["GET"])
@login_required
@check_verification
@check_user_info_complete
def get_chats_by_user_id(user_id):
    if current_user.id != user_id:
        return jsonify({"error": "Access denied"}), 403

    chats = Chat.get_all_by_user_id(user_id)
    if not chats:
        return jsonify({"message": "No chats found for this user"}), 200

    chat_models = [ChatListSchema.model_validate(chat).model_dump() for chat in chats]

    return jsonify(chat_models)


@message.route("/chat/<int:user_id>", methods=["GET"])
@login_required
@check_verification
@check_user_info_complete
def get_chat_by_user_id(user_id: int):
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
@check_verification
@check_user_info_complete
def streamed_response(prompt):
    def generate():
        response = generate_response(prompt, [])
        for res in response:
            for candidate in res._result.candidates:
                for part in candidate.content.parts:
                    print(f"data: {part.text}\n\n".encode())
                    yield f"data: {part.text}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return Response(generate(), content_type="text/event-stream")


@message.route("/chat/<int:chat_id>/delete", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def delete_chat_by_id(chat_id):
    chat = Chat.get_by_id(chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    if chat.user_id != current_user.id:
        print("Unauthorized attempt to delete chat")
        return jsonify({"error": "Wrong user id or chat id"}), 404

    messages = Message.get_by_chat_id(chat.id)

    if not messages:
        print("Messages not found")

    try:
        if messages:
            db.session.execute(delete(Message).where(Message.chat_id == chat_id))

        db.session.delete(chat)
        db.session.commit()

        return jsonify({"message": "Chat deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to delete chat: {str(e)}"}), 500


@message.route("/chat/<int:chat_id>/rename", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def rename_chat(chat_id):
    data = request.get_json()
    new_name = data.get("name", "").strip()

    if not new_name:
        return jsonify({"error": "Chat name cannot be empty"}), 400

    try:
        chat = Chat.get_by_id(chat_id)

        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        if chat.user_id != current_user.id:
            print("Unauthorized attempt to delete chat")
            return jsonify({"error": "Wrong user id or chat id"}), 404

        chat.name = new_name[:30]
        db.session.commit()

        return jsonify({"message": "Chat renamed successfully", "chat": {"id": chat.id, "name": chat.name}}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to rename chat: {str(e)}"}), 500


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
