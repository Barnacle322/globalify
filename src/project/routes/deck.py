import json

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from src.project.utils.enums import Status, StatusType

from ..extensions import db
from ..models import Deck, Feedback
from ..schemas.deck import DeckSchema, FeedbackHistorySchema, SummarySchema
from ..utils.funcs import calculate_md5, normalize_name
from ..utils.gemini import analyze_pdf
from ..utils.google_helpers.google_storage import load_deck, upload_deck, upload_picture_hd

deck = Blueprint("deck", __name__)
MAX_FILE_SIZE = 15 * 1024 * 1024  # bytes == 15mb


@deck.route("/list/<int:user_id>", methods=["GET"])
@login_required
def index(user_id):
    decks = Deck.get_by_user_id(user_id)
    return render_template(
        "deck/deck_list.html",
        decks=decks,
        current_user=current_user,
    )


@deck.route("/analysis", methods=["POST"])
@login_required
def process_deck():
    """Handles deck creation and analysis in one action."""
    deck_id = request.form.get("deck_id")
    if deck_id:
        deck = Deck.get_by_id(int(deck_id))
        if not deck:
            return jsonify({"error": "Deck not found"}), 404
        try:
            pdf_data = load_deck(deck.hash)  # type: ignore
        except Exception as e:
            print(f"Error loading deck: {e}")
            return jsonify({"error": "Error loading deck"}), 500
    else:
        if "file" not in request.files or request.files["file"] == "":
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        file_name = request.form.get("filename", "").strip()
        pdf_data = file.read()

        file_hash = calculate_md5(pdf_data)
        deck = Deck.get_by_hash(file_hash)

        if not deck:
            try:
                upload_deck(pdf_data, file_hash, "application/pdf")
                preview_file = request.files["preview_image"]
                deck_preview = preview_file.read()
                picture_url = upload_picture_hd(deck_preview)
                deck = Deck(name=file_name, hash=file_hash, picture_url=picture_url)
                deck.users.append(current_user)  # type: ignore
                db.session.add(deck)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return jsonify({"error": f"Error creating deck: {e}"}), 500

    goals = {key: request.form.get(key, "") for key in ["audience", "formality", "domain", "agent"]}
    try:
        existing_feedback = Feedback.get_by_deck_user_and_goals(
            deck_id=deck.id,
            user_id=current_user.id,
            audience=goals["audience"],
            formality=goals["formality"],
            domain=goals["domain"],
        )
        if existing_feedback:
            return redirect(url_for("deck.user_deck_detail", deck_id=deck.id, feedback_id=existing_feedback.id))

        try:
            print("Analyzing PDF")
            analysis_result_json = analyze_pdf(pdf_data, goals)  # type: ignore
            print("Analysis result JSON:", analysis_result_json)
            data = json.loads(analysis_result_json)
            print("Analysis result:", data)

        except Exception as e:
            print(f"Error analyzing PDF: {e}")
            db.session.rollback()
            raise e

        feedback = Feedback.create_from_json(analysis_data=data, goals=goals, current_user=current_user)  # type: ignore
        if feedback:
            deck.feedbacks.append(feedback)
        db.session.add(feedback)
        db.session.commit()
    except (json.JSONDecodeError, KeyError) as e:
        db.session.rollback()
        return jsonify({"error": "Error processing analysis"}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

    if feedback:
        return jsonify(
            {
                "deck_id": deck.id,
                "redirect_url": url_for("deck.user_deck_detail", deck_id=deck.id, feedback_id=feedback.id),
            }
        ), 200
    else:
        return jsonify({"error": "Feedback creation failed"}), 500


@deck.route("/feedbacks/<int:deck_id>", methods=["GET"])
@login_required
def user_deck_list(deck_id):
    feedback_models = Feedback.get_by_deck_id(deck_id)
    if not feedback_models:
        return jsonify({"error": "No feedbacks found"}), 404

    feedbacks = []

    for feedback in feedback_models:
        feedback_json = FeedbackHistorySchema(
            id=feedback.id,
            goals=[feedback.audience, feedback.formality, feedback.domain],
            created_at=feedback.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            formated_created_at=feedback.created_at.strftime("%d %b %Y %H:%M"),
            agent=normalize_name(feedback.agent) if feedback.agent else None,
        ).model_dump()
        feedbacks.append(feedback_json)

    return jsonify(
        {
            "feedbacks": [feedback for feedback in feedbacks],
        }
    )


@deck.route("/feedback/<int:feedback_id>/goals", methods=["GET"])
@login_required
def get_feedback_goals(feedback_id):
    feedback = Feedback.get_by_id(feedback_id)
    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404

    goals = {
        "audience": feedback.audience,
        "formality": feedback.formality,
        "domain": feedback.domain,
        "agent": feedback.agent,
    }

    return jsonify({"goals": goals}), 200


@deck.route("/<int:deck_id>/feedback/<int:feedback_id>", methods=["GET"])
@login_required
def user_deck_detail(deck_id, feedback_id):
    deck = Deck.get_by_id(deck_id)
    if not deck:
        return redirect(url_for("deck.index", _external=False, user_id=current_user.id))

    feedback = Feedback.get_by_id(feedback_id)

    return render_template("deck/deck_detail.html", deck=deck, feedback=feedback, user=current_user)


@deck.route("/file/<int:deck_id>")
@login_required
def deck_file(deck_id):
    deck = Deck.get_by_id(deck_id)
    if deck:
        try:
            deck_pdf = load_deck(deck.hash)  # type: ignore
            return jsonify({"deck": deck_pdf}), 200
        except Exception as e:
            print(f"Error loading deck: {e}")
            return jsonify({"error": "Error loading deck"}), 500
    else:
        return jsonify({"error": "Deck not found"}), 404


@deck.route("/<int:deck_id>", methods=["GET"])
@login_required
def get_deck(deck_id):
    deck = Deck.get_by_id(deck_id)
    if not deck:
        return jsonify({"error": "Deck not found"}), 404

    deck_json = DeckSchema(
        id=deck.id,
        name=deck.name,
        json_feedback=deck.feedbacks,
    )

    return jsonify(
        {
            "deck": deck_json.model_dump(),
        }
    )


@deck.route("scores/<int:feedback_id>", methods=["GET"])
@login_required
def get_deck_summary(feedback_id):
    feedback = Feedback.get_by_id(feedback_id)

    if not feedback:
        return jsonify({"error": "Feedback not found"}), 404
    summary_json = SummarySchema(
        id=feedback.id,
        clarity_score=feedback.clarity_score,
        grammar_score=feedback.grammar_score,
        design_score=feedback.design_score,
        storytelling_score=feedback.storytelling_score,
        engagement_score=feedback.engagement_score,
        overall_score=feedback.overall_score,
        recommendation=feedback.recommendation,
    )

    return jsonify(
        {
            "summary": summary_json.model_dump(),
        }
    )


@deck.route("/delete/<int:deck_id>", methods=["POST"])
@login_required
def delete_deck(deck_id):
    deck = Deck.get_by_id(deck_id)
    if not deck:
        status = Status(StatusType.ERROR, "Deck not found").get_status()
        return redirect(url_for("deck.index", _external=False, **status))

    try:
        db.session.delete(deck)
        db.session.commit()
        status = Status(StatusType.SUCCESS, "Deck deleted successfully").get_status()
    except Exception as e:
        db.session.rollback()
        status = Status(StatusType.ERROR, str(e)).get_status()

    return redirect(url_for("deck.index", _external=False, **status, user_id=current_user.id))


@deck.route("/update/<int:deck_id>", methods=["POST"])
@login_required
def update_deck(deck_id):
    deck = Deck.get_by_id(deck_id)
    if not deck:
        status = Status(StatusType.ERROR, "Deck not found").get_status()
        return redirect(url_for("deck.index", _external=False, **status, user_id=current_user.id))

    data = request.get_json()

    new_name = data.get("name", "").strip()
    print(new_name)
    if not new_name:
        status = Status(StatusType.ERROR, "Deck name is required").get_status()
        return redirect(url_for("deck.index", _external=False, **status, user_id=current_user.id))

    try:
        deck.name = new_name
        db.session.commit()
        status = Status(StatusType.SUCCESS, "Deck updated successfully").get_status()
    except Exception as e:
        db.session.rollback()
        status = Status(StatusType.ERROR, str(e)).get_status()

    return redirect(url_for("deck.index", _external=False, **status, user_id=current_user.id))


@deck.route("/feedback/delete/<int:feedback_id>", methods=["POST"])
@login_required
def delete_feedback(feedback_id):
    feedback = Feedback.get_by_id(feedback_id)
    if not feedback:
        status = Status(StatusType.ERROR, "Feedback not found").get_status()
        return redirect(url_for("deck.index", _external=False, **status))

    try:
        db.session.delete(feedback)
        db.session.commit()
        status = Status(StatusType.SUCCESS, "Feedback deleted successfully").get_status()
    except Exception as e:
        db.session.rollback()
        status = Status(StatusType.ERROR, str(e)).get_status()

    latest_feedback = Feedback.get_latest_by_deck_id(feedback.deck_id)
    if latest_feedback:
        return redirect(url_for("deck.user_deck_detail", deck_id=feedback.deck_id, feedback_id=latest_feedback.id))
    else:
        return redirect(url_for("deck.index", _external=False, **status, user_id=current_user.id))


@deck.route("/get/latest/feedback/<int:deck_id>", methods=["GET"])
@login_required
def get_latest_feedback(deck_id):
    deck = Deck.get_by_id(deck_id)
    if not deck:
        return jsonify({"error": "Deck not found"}), 404

    latest_feedback = Feedback.get_latest_by_deck_id(deck_id)

    if not latest_feedback:
        return jsonify({"error": "No feedback found for this deck"}), 404

    return jsonify({"feedback_id": latest_feedback.id}), 200
