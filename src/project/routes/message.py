import traceback

from flask import Blueprint, Response, jsonify, request, stream_with_context
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
    try:
        data = request.get_json()
        bot_message = data.get("bot_message", "").strip()
        user_message = data.get("user_message", "").strip()

        chat = Chat.get_by_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        if chat.user_id != current_user.id:
            return jsonify({"error": "Unauthorized access to chat"}), 403

        if user_message:
            user_msg = Message(chat_id=chat.id, message=user_message, type=SenderType.USER)
            db.session.add(user_msg)

        if bot_message:
            bot_msg = Message(chat_id=chat.id, message=bot_message, type=SenderType.GEMINI)
            db.session.add(bot_msg)

        db.session.commit()
        return jsonify({"message": "Chat saved successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to save chat: {str(e)}"}), 500


@message.route("/chat/<int:chat_id>/add-bot-message", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def add_bot_message(chat_id):
    try:
        data = request.get_json()
        bot_message = data.get("bot_message", "").strip()

        chat = Chat.get_by_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        if chat.user_id != current_user.id:
            return jsonify({"error": "Unauthorized access to chat"}), 403

        if bot_message:
            bot_msg = Message(chat_id=chat.id, message=bot_message, type=SenderType.GEMINI)
            db.session.add(bot_msg)
            db.session.commit()
            return jsonify({"message": "Bot message added successfully"}), 200

        return jsonify({"error": "No bot message provided"}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to add bot message: {str(e)}"}), 500


@message.route("/chat/create", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def create_chat():
    try:
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

        try:
            # Generate chat name - now handling a string response instead of a complex object
            bot_summary_text = generate_name_summary_with_typesense_context(user_message)
            # Limit name length and provide fallback if empty
            chat.name = bot_summary_text[:30] if bot_summary_text else "New Chat"
        except Exception as e:
            # Fallback if name generation fails
            chat.name = "New Chat"
            print(f"Error generating chat name: {str(e)}")

        db.session.commit()

        serialized_chat = ChatSchema(
            id=chat.id, user_id=chat.user_id, created=chat.created, name=chat.name, messages=None
        ).model_dump_json()

        return jsonify(
            {
                "user_message": user_message,
                "bot_summary_text": chat.name,
                "chat": serialized_chat,
            }
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to create chat: {str(e)}"}), 500


@message.route("/chat/<int:chat_id>/details", methods=["GET"])
@login_required
@check_verification
@check_user_info_complete
def get_chat_details(chat_id):
    try:
        chat = Chat.get_by_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        if chat.user_id != current_user.id:
            return jsonify({"error": "Unauthorized access to chat"}), 403

        messages = Message.get_by_chat_id(chat.id)
        message_models = [MessageSchema.model_validate(msg) for msg in messages] if messages else []
        chat_model = ChatSchema(
            id=chat.id, user_id=chat.user_id, name=chat.name, created=chat.created, messages=message_models
        )

        return jsonify(chat_model.model_dump())
    except Exception as e:
        return jsonify({"error": f"Failed to get chat details: {str(e)}"}), 500


@message.route("/chats/<int:user_id>", methods=["GET"])
@login_required
@check_verification
@check_user_info_complete
def get_chats_by_user_id(user_id):
    try:
        if current_user.id != user_id:
            return jsonify({"error": "Access denied"}), 403

        chats = Chat.get_all_by_user_id(user_id)
        if not chats:
            return jsonify([]), 200

        chat_models = [ChatListSchema.model_validate(chat).model_dump() for chat in chats]
        return jsonify(chat_models)
    except Exception as e:
        return jsonify({"error": f"Failed to get chats: {str(e)}"}), 500


@message.route("/stream", methods=["GET"])
@login_required
@check_verification
@check_user_info_complete
def streamed_response():
    def generate():
        prompt = request.args.get("prompt", "").strip()

        if not prompt:
            yield b'data: {"error": "Empty prompt"}\n\n'
            yield b"data: [DONE]\n\n"
            return

        chat_id = request.args.get("chat_id", type=int)
        try:
            old_messages = []
            if chat_id:
                chat = Chat.get_by_id(chat_id)
                if not chat or chat.user_id != current_user.id:
                    yield b'data: {"error": "Chat not found or unauthorized access"}\n\n'
                    yield b"data: [DONE]\n\n"
                    return

                messages = Message.get_by_chat_id(chat_id)
                old_messages = (
                    [
                        {"role": "user" if msg.type == SenderType.USER else "model", "parts": [msg.message]}
                        for msg in messages
                    ]
                    if messages
                    else []
                )

            # Add the current prompt to messages
            old_messages.append({"role": "user", "parts": [prompt]})
            response = generate_response(prompt, old_messages)

            # Handle chunks properly based on the API response format
            for chunk in response:
                if hasattr(chunk, "text") and chunk.text:
                    # Send each chunk properly formatted for SSE
                    # Ensure each chunk ends with a double newline
                    text = chunk.text
                    if text.strip():  # Only send non-empty chunks
                        yield f"data: {text}\n\n".encode()

                # No need to handle function calls since they're handled by the SDK

            # Signal the end of the stream
            yield b"data: [DONE]\n\n"

        except Exception as e:
            error_message = str(e)
            print(f"Error in stream: {error_message}")
            yield f'data: {{"error": "{error_message}"}}\n\n'.encode()
            yield b"data: [DONE]\n\n"

    return Response(stream_with_context(generate()), content_type="text/event-stream")


@message.route("/chat/<int:chat_id>/delete", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def delete_chat_by_id(chat_id):
    try:
        chat = Chat.get_by_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        if chat.user_id != current_user.id:
            return jsonify({"error": "Unauthorized access to chat"}), 403

        # Delete related messages first
        db.session.execute(delete(Message).where(Message.chat_id == chat_id))
        db.session.delete(chat)
        db.session.commit()

        return jsonify({"message": "Chat deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting chat: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to delete chat: {str(e)}"}), 500


@message.route("/chat/<int:chat_id>/rename", methods=["POST"])
@login_required
@check_verification
@check_user_info_complete
def rename_chat(chat_id):
    try:
        data = request.get_json()
        new_name = data.get("name", "").strip()

        if not new_name:
            return jsonify({"error": "Chat name cannot be empty"}), 400

        chat = Chat.get_by_id(chat_id)
        if not chat:
            return jsonify({"error": "Chat not found"}), 404

        if chat.user_id != current_user.id:
            return jsonify({"error": "Unauthorized access to chat"}), 403

        chat.name = new_name[:30]
        db.session.commit()

        return jsonify({"message": "Chat renamed successfully", "chat": {"id": chat.id, "name": chat.name}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to rename chat: {str(e)}"}), 500
