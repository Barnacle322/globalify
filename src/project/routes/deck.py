import json

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import Deck, Scores
from ..utils.funcs import calculate_md5
from ..utils.gemini import analyze_pdf

deck = Blueprint("deck", __name__)


@deck.route("/", methods=["GET"])
@login_required
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template(
        "deck/deck_upload.html",
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

    if file.filename == "":
        print("No selected file")
        return render_template(
            "deck.html",
            status_type=status_type,
            msg=msg,
        )

    pdf_data = file.read()
    print("File loaded successfully")
    print(f"Size: {len(pdf_data)} bytes")

    file_hash = calculate_md5(pdf_data)
    # if Deck.check_hash(file_hash):  # Commented for testing
    #     print("Deck with this file already exists. Skipping analysis.")
    #     return redirect(
    #         url_for(
    #             "index",
    #             status_type=status_type,
    #             msg=msg,
    #         )
    #     )

    analysis_result_json = analyze_pdf(pdf_data)
    print(analysis_result_json)

    if analysis_result_json:
        deck, scores = create_models_from_json(analysis_result_json, file_hash)
        if deck and scores:
            print("Success")
        else:
            print("Error")

    return jsonify({"redirect_url": url_for("deck.deck_results", deck_id=deck.id)}), 200  # type: ignore


@deck.route("/deck_results/<int:deck_id>")
@login_required
def deck_results(deck_id):
    deck = Deck.get_by_id(deck_id)
    if deck:
        return jsonify({"deck": deck.to_dict(), "scores": deck.scores.to_dict()}), 200
    else:
        return redirect(url_for("index"))


def create_models_from_json(json_data: str, unique_hash: str):
    try:
        data = json.loads(json_data)

        deck = Deck(
            user_id=current_user.id,
            hash=unique_hash,
            overall_recommendation=data.get("overall_recommendation"),
            json_feedback=data.get("deck_feedback"),
        )

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


@deck.route("/upload/<username>", methods=["GET"])
@login_required
def deck_upload(username):
    return render_template("gemini_presentation/presentation_upload_page.html")


