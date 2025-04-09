from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    url_for,
)

from ..extensions import db
from ..models import ( Company)
from ..models.microwebpage import MicroWebPage, WebpageMedia
from ..utils.enums import Status, StatusType
from ..utils.errors.error_messages import PICTURE_NOT_LOADED
from ..utils.google_helpers.google_storage import upload_picture, upload_picture_for_web_page

microwebpage = Blueprint("micropage", __name__)




@microwebpage.get("/webpage/<int:microwebpage_id>")
def get_micro_web_page(microwebpage_id):
    print(microwebpage_id)
    micro_web_page = MicroWebPage.get_by_id(microwebpage_id)
    company = micro_web_page.company
    print(micro_web_page.logo_url)
    return render_template("microwebpage/micro_web_page.html", microwebpage=micro_web_page, company=company)



@microwebpage.route("/create/<int:company_id>", methods=["GET", "POST"])
def create_micro_web_page(company_id):
    company = Company.get_by_id(company_id)
    if not company:
        return jsonify({"error": "Company does not exist!"}), 400

    if company.microwebpage:
        return render_template("microwebpage/micro_web_page.html", microwebpage=company.microwebpage, company=company)

    if request.method == "POST":
        description = request.form.get("description")
        mission_statement = request.form.get("mission_statement")
        target_market = request.form.get("target_market")
        key_products = request.form.get("key_products")
        awards = request.form.get("awards")
        partnerships = request.form.get("partnerships")
        team_description = request.form.get("team_description")
        customer_testimonials = request.form.get("customer_testimonials")
        founder_bio = request.form.get("founder_bio")
        assets = request.form.get("assets")
        logo = request.files.get("logo")
        uploaded_images = request.files.getlist("images[]")

        # Validate required fields
        if not description:
            return jsonify({"error": "Description is required"}), 400
        if not mission_statement:
            return jsonify({"error": "Mission statement is required"}), 400

        company = Company.get_by_id(company_id)
        if not company:
            return jsonify({"error": "Invalid company ID"}), 400

        # Create new micro webpage
        new_micropage = MicroWebPage(
            company=company,
            company_id=company_id,
            description=description,
            mission_statement=mission_statement,
            target_market=target_market,
            key_products=key_products,
            awards=awards,
            partnerships=partnerships,
            team_description=team_description,
            customer_testimonials=customer_testimonials,
            founder_bio=founder_bio,
            assets=assets,
        )

        # Handle logo upload if present
        if logo:
            try:
                logo_url = upload_picture(logo)
                new_micropage.logo_url = logo_url
            except Exception as e:
                print(f"Error uploading logo: {str(e)}")
                # Continue without logo if upload fails
                pass

        db.session.add(new_micropage)
        db.session.flush()
        # db.session.commit()
        # Handle multiple image uploads
        if uploaded_images:
            for image in uploaded_images:
                if image and image.filename:  # Check if the file is valid
                    try:
                        image_url = upload_picture_for_web_page(image)  # Assuming upload_picture returns a URL
                        new_photo = WebpageMedia(
                            micro_webpage_id=new_micropage.id,
                            picture_url=image_url,
                        )
                        db.session.add(new_photo)
                    except Exception as e:
                        print(f"Error uploading image: {str(e)}")
                        # Continue with the next image if one fails
                        continue
        db.session.commit()

        return jsonify({
            "redirect_url": url_for("micropage.get_micro_web_page", microwebpage_id=new_micropage.id)
        }), 200

    return render_template("microwebpage/create_micro_web_page.html", company=company)
