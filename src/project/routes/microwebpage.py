from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    url_for,
)

from ..extensions import db
from ..models import ( Company)
from ..models.microwebpage import MicroWebPage

microwebpage = Blueprint("micropage", __name__)




@microwebpage.get("/webpage/<int:microwebpage_id>")
def get_micro_web_page(microwebpage_id):
    print(microwebpage_id)
    micro_web_page = MicroWebPage.get_by_id(microwebpage_id)
    company = micro_web_page.company
    return render_template("microwebpage/micro_web_page.html", microwebpage=micro_web_page, company=company)



@microwebpage.route("/create/<int:company_id>", methods=["GET", "POST"])
def create_micro_web_page(company_id):
    company = Company.get_by_id(company_id)
    if not company:
        return jsonify({"error": "Company does not exist!"}), 400

    if company.microwebpage:
        return render_template("microwebpage/micro_web_page.html", microwebpage=company.microwebpage.id, company=company)
    if request.method == "POST":
        data = request.get_json()
        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        description = data.get("description")
        assets = data.get("assets")
        mission_statement = data.get("mission_statement")
        target_market = data.get("target_market")
        key_products = data.get("key_products")
        awards = data.get("awards")
        partnerships = data.get("partnerships")
        team_description = data.get("team_description")
        customer_testimonials = data.get("customer_testimonials")
        founder_bio = data.get("founder_bio")

        # Validate required fields
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
            mission_statement=mission_statement,
            target_market=target_market,
            key_products=key_products,
            awards=awards,
            partnerships=partnerships,
            team_description=team_description,
            customer_testimonials=customer_testimonials,
            founder_bio=founder_bio,
        )

        db.session.add(new_micropage)
        db.session.commit()

        return jsonify({"redirect_url": url_for("micropage.get_micro_web_page", microwebpage_id=new_micropage.id)}), 200

    return render_template("microwebpage/create_micro_web_page.html", company=company)

