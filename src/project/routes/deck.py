import json

from flask import Blueprint, Request, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import inspect

from src.project.utils.enums import Status, StatusType

from ..extensions import db
from ..models import Deck, Feedback
from ..schemas.deck import DeckSchema, SummarySchema
from ..utils.funcs import calculate_md5
from ..utils.gemini import analyze_pdf
from ..utils.google_helpers.google_storage import load_deck, upload_deck

deck = Blueprint("deck", __name__)
MAX_FILE_SIZE = 15 * 1024 * 1024  # bytes == 15mb


@deck.route("/list/<int:user_id>", methods=["GET"])
@login_required
def index(user_id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    decks = Deck.get_by_user_id(user_id)
    return render_template(
        "deck/deck_list.html",
        decks=decks,
        current_user=current_user,
        status_type=status_type,
        msg=msg,
    )


@deck.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if "file" not in request.files or request.files["file"] == "":
        print("No file part")
        return render_template(
            "deck/deck_upload.html",
            status_type=status_type,
            msg=msg,
        )

    file = request.files["file"]
    pdf_data = file.read()

    print(f"File loaded successfully \nSize: {len(pdf_data)} bytes")

    if len(pdf_data) > MAX_FILE_SIZE:
        print("Too big file")
        return render_template(
            "deck.html",
            status_type=status_type,
            msg=msg,
        )

    file_hash = calculate_md5(pdf_data)
    existing_deck = Deck.get_by_hash(file_hash)
    if existing_deck:
        if inspect(current_user) not in [inspect(user) for user in existing_deck.users]:
            existing_deck.users.append(current_user)  # type: ignore
            db.session.commit()
            print(f"User {current_user.id} added to deck {existing_deck.id}")

            deck = existing_deck
    else:
        try:
            upload_deck(pdf_data, file_hash, "application/pdf")

            deck = Deck(
                # picture_url=picture_url,
                hash=file_hash,
            )
            deck.users.append(current_user)  # type: ignore

            db.session.add(deck)
            db.session.commit()

        except Exception as e:
            print(f"Error creating  pitch deck: {e}")
            db.session.rollback()
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("deck.index", _external=False, **status))

    return jsonify(deck_id=deck.id), 200


@deck.route("/analysis", methods=["GET", "POST"])
@login_required
def analyze():
    deck_id = request.form.get("deck_id", type=int)

    if not deck_id:
        status = Status(StatusType.ERROR, "Error fetching  pitch deck ID").get_status()
        return redirect(url_for("deck.index", _external=False, **status))

    goals = {key: request.form.get(key, "") for key in ["audience", "formality", "domain"]}

    if Feedback.get_by_deck_user_and_goals(
        deck_id, current_user.id, goals["audience"], goals["formality"], goals["domain"]
    ):
        print("Feedback with selected goals for this deck already exists.")
        return jsonify({"redirect_url": url_for("deck.user_deck_detail", deck_id=deck_id)}), 200

    pdf_data = request.files["file"].read()
    analysis_result_json = analyze_pdf(pdf_data, goals)
    deck = Deck.get_by_id(deck_id)

    if deck:
        try:
            data = json.loads(analysis_result_json)
            feedback = Feedback.create_from_json(data, current_user)  # type: ignore
            deck.name = data["deck_name"]
            deck.feedbacks.append(feedback)

            db.session.add(feedback)
            db.session.add(deck)

            db.session.commit()

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error decoding JSON or accessing key: {e}")
            deck.name = "Default Deck Name"
        except Exception as e:
            status = Status(StatusType.ERROR, str(e)).get_status()
            return redirect(url_for("deck.user_deck_list", _external=False, **status))

    return jsonify({"redirect_url": url_for("deck.user_deck_detail", deck_id=deck_id)}), 200


@deck.route("/detail/<int:deck_id>", methods=["GET"])
@login_required
def user_deck_detail(deck_id):
    deck = Deck.get_by_id(deck_id)
    if not deck:
        return render_template(
            "deck_list.html",
        )
    return render_template("deck/deck_detail.html", deck=deck, user=current_user)


@deck.route("/file/<int:deck_id>")
@login_required
def deck_file(deck_id):
    deck = Deck.get_by_id(deck_id)
    try:
        deck_pdf = load_deck(deck.hash)  # type: ignore
        return jsonify({"deck": deck_pdf}), 200

    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("deck.user_deck_list", _external=False, **status))


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


# @deck.route("scores/<int:deck_id>", methods=["GET"])
# @login_required
# def get_deck_summary(deck_id):
#     scores = Feedback.get_by_deck_id(deck_id)
#     deck = Deck.get_by_id(deck_id)
#     if not deck or not scores:
#         return jsonify({"error": "Scores/Deck not found"}), 404

#     summary_json = SummarySchema(
#         id=scores.id,
#         clarity=scores.clarity,
#         grammary=scores.grammary,
#         storytelling=scores.storytelling,
#         completeness=scores.completeness,
#         engagement=scores.engagement,
#         overall_score=deck.overall_score,
#         recommandation=deck.overall_recommendation,
#     )

#     return jsonify(
#         {
#             "summary": summary_json.model_dump(),
#         }
#     )


@deck.route("/delete/<int:deck_id>", methods=["POST"])
@login_required
def delete_deck(deck_id):
    deck = Deck.get_by_id(deck_id)
    if not deck:
        status = Status(StatusType.ERROR, "Deck not found").get_status()
        return redirect(url_for("deck.user_deck_list", _external=False, **status))

    try:
        db.session.delete(deck)
        db.session.commit()
        status = Status(StatusType.SUCCESS, "Deck deleted successfully").get_status()
    except Exception as e:
        db.session.rollback()
        status = Status(StatusType.ERROR, str(e)).get_status()

    return redirect(url_for("deck.index", _external=False, **status, user_id=current_user.id))
