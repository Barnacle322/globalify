from datetime import datetime

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
)
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


@presentation.route("/upload", methods=["GET"])
@login_required
def upload_presentation():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")
   
    return render_template(
        "presentation.html",
        status_type=status_type,
        msg=msg,
    )
