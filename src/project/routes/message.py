from flask import Blueprint, Response, jsonify, request, stream_with_context, render_template
from flask_login import current_user, login_required
from sqlalchemy import delete

from ..extensions import db
from ..models import (
    Chat,
    Message,
)
from ..schemas.message import ChatListSchema, ChatSchema, MessageSchema
from ..utils.decorators import check_user_info_complete, check_verification
from ..utils.enums import SenderType
from ..utils.gemini import generate_name_summary_with_typesense_context, generate_response

message = Blueprint("message", __name__)


@message.route("/chat/<int:chat_id>/save-messages", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def save_chat(chat_id):
    data = request.get_json()
    bot_message = data.get("bot_message", "").strip()
    user_message = data.get("user_message", "").strip()

    chat = Chat.get_by_id(chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    user_msg = Message(chat_id=chat.id, message=user_message, type=SenderType.USER)
    db.session.add(user_msg)

    if bot_message:
        bot_msg = Message(chat_id=chat.id, message=bot_message, type=SenderType.GEMINI)
        db.session.add(bot_msg)
    db.session.commit()

    return jsonify({"message": "Chat saved successfully"}), 200


@message.route("/chat/<int:chat_id>/add-bot-message", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def add_bot_message(chat_id):
    data = request.get_json()
    bot_message = data.get("bot_message", "").strip()

    chat = Chat.get_by_id(chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    if bot_message:
        bot_msg = Message(chat_id=chat.id, message=bot_message, type=SenderType.GEMINI)
        db.session.add(bot_msg)
        db.session.commit()
        return jsonify({"message": "Bot message added successfully"}), 200

    return jsonify({"error": "No bot message provided"}), 400


@message.route("/chat/create", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def create_chat():
    data = request.get_json()
    user_message = data.get("user_message", "").strip()
    bot_message = data.get("bot_message", "").strip()

    if not user_message or not bot_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    chat = Chat(user_id=current_user.id)
    db.session.add(chat)
    db.session.commit()

    user_msg = Message(chat_id=chat.id, message=user_message, type=SenderType.USER)
    db.session.add(user_msg)

    bot_msg = Message(chat_id=chat.id, message=bot_message, type=SenderType.GEMINI)
    db.session.add(bot_msg)
    db.session.commit()

    summary_bot_summary = generate_name_summary_with_typesense_context(user_message)

    bot_summary_text = ""
    for res in summary_bot_summary:
        for candidate in res._result.candidates:
            for part in candidate.content.parts:
                bot_summary_text += part.text

    bot_summary_text = bot_summary_text.strip()

    chat.name = bot_summary_text
    db.session.commit()

    serialized_chat = ChatSchema(
        id=chat.id, user_id=chat.user_id, created=chat.created, name=chat.name, messages=None
    ).model_dump_json()

    return jsonify(
        {
            "user_message": user_message,
            "bot_summary_text": bot_summary_text,
            "chat": serialized_chat,
        }
    )


@message.route("/chat/<int:chat_id>/details", methods=["GET"])
@login_required
@check_verification
@check_user_info_complete
def get_chat_details(chat_id):
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


@message.route("/stream", methods=["GET"])
@login_required
@check_verification
@check_user_info_complete
def streamed_response():
    def generate():
        prompt = request.args.get("prompt")

        if not prompt:
            yield b"data: [DONE]\n\n"
            return

        chat_id = request.args.get("chat_id", type=int)
        if chat_id:
            messages = Message.get_by_chat_id(chat_id)

            old_messages = [
                {"role": "user" if msg.type == SenderType.USER else "model", "parts": [msg.message]} for msg in messages
            ]

            old_messages.append({"role": "user", "parts": [prompt]})
            response = generate_response(prompt, old_messages)
        else:
            response = generate_response(prompt, [])

        for res in response:
            for candidate in res._result.candidates:
                for part in candidate.content.parts:
                    print(f"data: {part.text}\n\n".encode())
                    yield f"data: {part.text}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream")


@message.route("/chat/<int:chat_id>/delete", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def delete_chat_by_id(chat_id):
    chat = Chat.get_by_id(chat_id)
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    if chat.user_id != current_user.id:
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
            return jsonify({"error": "Wrong user id or chat id"}), 404

        chat.name = new_name[:30]
        db.session.commit()

        return jsonify({"message": "Chat renamed successfully", "chat": {"id": chat.id, "name": chat.name}}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to rename chat: {str(e)}"}), 500




