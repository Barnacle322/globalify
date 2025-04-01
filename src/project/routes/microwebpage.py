from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
    Response,
)

from ..extensions import db
from ..models import (
    Chat,
    Message,
)

micropage = Blueprint("micropage", __name__)



@micropage.get("/<int:micropage_id>")
def get_micropage(micropage_id):
    return render_template(
        "microwebpage/testwebpage.html",
    )

@micropage.get("/create")
def create_micropage():
    return render_template(
        "microwebpage/create_micropage.html",
    )
