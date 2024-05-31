import re
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import (
    Company,
    InvestmentFirm,
    Investor,
)
from ..utils.enums import NotificationDestination, Status, StatusType
from ..utils.errors.error_messages import NOT_AUTHORIZED
from ..utils.suggestion import WEIGHTS, check_weights

admin = Blueprint("admin", __name__)


@admin.route("/dashboard")
def admin_investor_view():
    investors = Investor.get_all()

    print(investors)

    return render_template("admin/investor.html", investors=investors)
