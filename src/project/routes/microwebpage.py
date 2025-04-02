from _pydatetime import datetime

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
    Message, Company,
)
from ..models.microwebpage import MicroWebPage

microwebpage = Blueprint("micropage", __name__)



@microwebpage.get("/<int:micropage_id>")
def get_micro_web_page(micropage_id):
    micropage = MicroWebPage.get_by_id(micropage_id)
    if not micropage:
        return jsonify({"error": "Micro Web Page not found"}), 404

    return render_template("microwebpage/micro_web_page.html",micropage=micropage, company=micropage.company)

@microwebpage.post("/create")
def create_micro_web_page():
    company_id = request.form.get("company_id", type=int)
    description = request.form.get("description")
    assets = request.form.get("assets")

    if not company_id:
        return jsonify({"error": "Company ID is required"}), 400
    if not description:
        return jsonify({"error": "Description is required"}), 400
    if not assets:
        return jsonify({"error": "Logo URL is required"}), 400


    company = Company.get_by_id(company_id)
    if not company:
        return jsonify({"error": "Invalid company ID"}), 400

    new_micropage = MicroWebPage(
        company=company,
        company_id=company_id,
        description=description,
        assets=assets,
    )


    db.session.add(new_micropage)
    db.session.commit()

    # Return success response
    return jsonify({"redirect_url": url_for("micropage.get_micro_web_page", micropage_id=new_micropage.id)}), 200
