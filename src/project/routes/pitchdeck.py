import json

from flask import Blueprint, redirect, render_template, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import DeckList, PitchDeck, Scores
from ..utils.gemini import analyze_pdf

pitchdeck = Blueprint("pitchdeck", __name__)


@pitchdeck.route("/", methods=["GET"])
@login_required
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template(
        "pitch_deck.html",
        status_type=status_type,
        msg=msg,
    )


@pitchdeck.route("/analysis", methods=["GET", "POST"])
@login_required
def analyze_pitch_deck_route():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if "file" not in request.files:
        print("No file part")
        return render_template(
            "pitch_deck.html",
            status_type=status_type,
            msg=msg,
        )

    file = request.files["file"]

    if file.filename == "":
        print("No selected file")
        return render_template(
            "pitch_deck.html",
            status_type=status_type,
            msg=msg,
        )

    try:
        pdf_data = file.read()
        print("File loaded successfully")
        print(f"Size: {len(pdf_data)} bytes")

        analysis_result_json = analyze_pdf(pdf_data)
        print(analysis_result_json)

        if analysis_result_json:
            unique_id = file.filename + str(len(pdf_data))  # type: ignore
            pitch_deck = create_models_from_json(analysis_result_json, unique_id)
            if pitch_deck:
                print("Success")
            else:
                print("Error")

    except Exception as e:
        print(f"Error: {e}")
        status_type = "danger"
        msg = f"An error occurred: {e}"

    return render_template(
        "pitch_deck.html",
        status_type=status_type,
        msg=msg,
    )


def create_models_from_json(json_data: str, unique_id: str):
    try:
        data = json.loads(json_data)

        pitch_deck = PitchDeck(
            user_id=current_user.id,
            unique_id=unique_id,
            summary=data.get("summary"),
            overall_recommendation=data.get("overall_recommendation"),
        )

        scores = Scores(
            clarity=data["scores"].get("clarity"),
            grammary=data["scores"].get("grammar"),
            storytelling=data["scores"].get("storytelling"),
            completeness=data["scores"].get("completeness"),
            engagement=data["scores"].get("engagement"),
            pitch_deck=pitch_deck,
        )

        deck_lists = []
        for page_data in data.get("page_feedback", []):
            deck_list = DeckList(
                page_number=page_data.get("page_number"), feed_back=page_data.get("feedback"), pitch_deck=pitch_deck
            )
            deck_lists.append(deck_list)

        db.session.add(pitch_deck)
        db.session.commit()

        return pitch_deck

    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        db.session.rollback()
        return None, None, None
    except Exception as e:
        print(f"Error creating models: {e}")
        db.session.rollback()
        return None, None, None
