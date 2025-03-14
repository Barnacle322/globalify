import json

from flask import Blueprint, redirect, render_template, request
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
        "deck.html",
        status_type=status_type,
        msg=msg,
    )


@deck.route("/analysis", methods=["GET", "POST"])
@login_required
def analyze_deck_route():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if "file" not in request.files:
        print("No file part")
        return render_template(
            "deck.html",
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

    try:
        pdf_data = file.read()
        print("File loaded successfully")
        print(f"Size: {len(pdf_data)} bytes")

        file_hash = calculate_md5(pdf_data)
        if Deck.check_hash(file_hash):
            print("Deck with this file already exists. Skipping analysis.")
            return render_template(
                "deck.html",
                status_type=status_type,
                msg=msg,
            )

        analysis_result_json = analyze_pdf(pdf_data)
        print(analysis_result_json)

        if analysis_result_json:
            deck = create_models_from_json(analysis_result_json, file_hash)
            if deck:
                print("Success")
            else:
                print("Error")

    except Exception as e:
        print(f"Error: {e}")
        status_type = "danger"
        msg = f"An error occurred: {e}"

    return render_template(
        "deck.html",
        status_type=status_type,
        msg=msg,
    )


def create_models_from_json(json_data: str, unique_hash: str):
    try:
        data = json.loads(json_data)

        deck = Deck(
            user_id=current_user.id,
            hash=unique_hash,
            overall_recommendation=data.get("overall_recommendation"),
            json_feedback=data.get("deck_feedback"),
        )

        _ = Scores(
            clarity=data["scores"].get("clarity"),
            grammary=data["scores"].get("grammar"),
            storytelling=data["scores"].get("storytelling"),
            completeness=data["scores"].get("completeness"),
            engagement=data["scores"].get("engagement"),
            deck=deck,
        )

        db.session.add(deck)
        db.session.commit()

        return deck

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        db.session.rollback()
        return None, None, None
    except Exception as e:
        print(f"Error creating models: {e}")
        db.session.rollback()
        return None, None, None



@deck.route("/upload/<username>", methods=["GET"])
@login_required
def deck_upload(username):
    return render_template("gemini_presentation/presentation_upload_page.html")


