import json

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import inspect

from src.project.utils.enums import Status, StatusType

from ..extensions import db
from ..models import Deck, Scores
from ..utils.funcs import calculate_md5
from ..utils.gemini import analyze_pdf
from ..utils.google_helpers.google_storage import load_deck, upload_deck

deck = Blueprint("deck", __name__)
MAX_FILE_SIZE = 15728640


@deck.route("/list/<int:user_id>", methods=["GET"])
@login_required
def index(user_id):
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    decks = Deck.get_by_user_id(user_id)
    print(decks)
    return render_template(
        "deck/deck_list.html",
        decks=decks,
        current_user=current_user,
        status_type=status_type,
        msg=msg,
    )


@deck.route("/analysis", methods=["GET", "POST"])
@login_required
def analyze_deck():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if "file" not in request.files:
        print("No file part")
        return render_template(
            "deck/deck_upload.html",
            status_type=status_type,
            msg=msg,
        )

    file = request.files["file"]

    if file == "":
        print("No selected file")
        return render_template(
            "deck.html",
            status_type=status_type,
            msg=msg,
        )

    audience = request.form.get("audience", "")
    formality = request.form.get("formality", "")
    domain = request.form.get("domain", "")

    pdf_data = file.read()
    print("File loaded successfully")
    print(f"Size: {len(pdf_data)} bytes")

    # if len(pdf_data) > MAX_FILE_SIZE:
    #     print("Too big file")
    #     return render_template(
    #         "deck.html",
    #         status_type=status_type,
    #         msg=msg,
    #     )

    file_hash = calculate_md5(pdf_data)
    existing_deck = Deck.get_by_hash(file_hash)
    if existing_deck:
        print("Deck with this hash already exists. Skipping analysis.")

        if inspect(current_user) not in [inspect(user) for user in existing_deck.users]:
            existing_deck.users.append(current_user)  # type: ignore
            db.session.commit()
            print(f"User {current_user.id} added to deck {existing_deck.id}")
        deck_id = existing_deck.id

    else:
        analysis_result_json = analyze_pdf(pdf_data, audience, formality, domain)
        print(analysis_result_json)

        if analysis_result_json:
            deck, scores = create_models_from_json(analysis_result_json, file_hash, file.filename)
            if deck and scores:
                upload_deck(pdf_data, "application/pdf", file_hash)
                print("Success")
                deck_id = deck.id
            else:
                print("Error")

    return jsonify({"redirect_url": url_for("deck.user_deck_detail", deck_id=deck_id)}), 200


def create_models_from_json(json_data: str, unique_hash: str, deck_name: str | None):
    try:
        data = json.loads(json_data)

        deck = Deck(
            hash=unique_hash,
            # name=deck_name or unique_hash,
            overall_recommendation=data.get("overall_recommendation"),
            json_feedback=data.get("deck_feedback"),
        )
        deck.users.append(current_user)  # type: ignore

        scores = Scores(
            clarity=data["scores"].get("clarity"),
            grammary=data["scores"].get("grammar"),
            storytelling=data["scores"].get("storytelling"),
            completeness=data["scores"].get("completeness"),
            engagement=data["scores"].get("engagement"),
            deck=deck,
        )

        db.session.add(deck)
        db.session.commit()

        return deck, scores

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        db.session.rollback()
        return None, None
    except Exception as e:
        print(f"Error creating models: {e}")
        db.session.rollback()
        return None, None


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
        deck_pdf = load_deck(deck.hash)
        return jsonify({"deck": deck_pdf}), 200

    except Exception as e:
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("deck.user_deck_list", _external=False, **status))


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
