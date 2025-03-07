from flask import Blueprint, redirect, render_template, request
from flask_login import login_required

from ..extensions import db
from ..models import Presentation

presentation = Blueprint("presentation", __name__)


@presentation.route("/", methods=["GET"])
@login_required
def index():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    return render_template(
        "presentation.html",
        status_type=status_type,
        msg=msg,
    )


presentation.route("/upload", methods=["GET", "POST"])


@presentation.route("/upload", methods=["GET", "POST"])
@login_required
def upload_presentation():
    # Обработка GET-запроса (отображение формы)
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    if "file" not in request.files:
        print("No file part")
        return render_template(
            "presentation.html",
            status_type=status_type,
            msg=msg,
        )

    file = request.files["file"]

    if file.filename == "":
        print("No selected file")
        return render_template(
            "presentation.html",
            status_type=status_type,
            msg=msg,
        )

    try:
        pdf_data = file.read()
        print("File loaded successfully")
        print(f"Size: {len(pdf_data)} bytes")

    except Exception as e:
        print(f"Error: {e}")

    return render_template(
        "presentation.html",
        status_type=status_type,
        msg=msg,
    )
