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
    micro_web_page = MicroWebPage.get_by_id(microwebpage_id)
    company = micro_web_page.company
    return render_template("microwebpage/micro_web_page.html", microwebpage=micro_web_page, company=company)



@microwebpage.route("/create/<int:company_id>", methods=["GET", "POST"])
def create_micro_web_page(company_id):
    company = Company.get_by_id(company_id)
    if not company:
        return jsonify({"error": "Company does not exist!"}), 400

    if company.microwebpage:
        return render_template("microwebpage/micro_web_page.html", microwebpage=company.microwebpage, company=company)

    if request.method == "POST":
        required_fields = {
            "hero_title": "Hero title is required",
            "hero_subtitle": "Hero subtitle is required",
            "mission_title": "Mission title is required",
            "mission_statement": "Mission statement is required",
            "leadership_title": "Leadership title is required",
            "leadership_subtitle": "Leadership subtitle is required",
            "customer_testimonials_title": "Customer testimonials title is required",
            "customer_testimonials_subtitle": "Customer testimonials subtitle is required",
        }

        form_data = {}
        for field, error_msg in required_fields.items():
            value = request.form.get(field)
            if not value:
                return jsonify({"error": error_msg}), 400
            form_data[field] = value  # store the valid field for later use


        uploaded_images = request.files.getlist("images[]")
        logo = request.files.get("logo")

        # Optional fields
        customer_testimonials = request.form.get("customer_testimonials")
        team_title = request.form.get("team_title")
        team_subtitle = request.form.get("team_subtitle")
        uploaded_images = request.files.getlist("images[]")
        description = request.form.get("description")
        target_market = request.form.get("target_market")
        key_products = request.form.get("key_products")
        awards = request.form.get("awards")
        partnerships = request.form.get("partnerships")
        team_description = request.form.get("team_description")
        founder_bio = request.form.get("founder_bio")
        assets = request.form.get("assets")

        # Now use both required and optional data to create the object
        new_micropage = MicroWebPage(
            company=company,
            company_id=company_id,
            hero_title=form_data["hero_title"],
            hero_subtitle=form_data["hero_subtitle"],
            mission_title=form_data["mission_title"],
            mission_statement=form_data["mission_statement"],
            leadership_title=form_data["leadership_title"],
            leadership_subtitle=form_data["leadership_subtitle"],
            customer_testimonials_title=form_data["customer_testimonials_title"],
            customer_testimonials_subtitle=form_data["customer_testimonials_subtitle"],
            team_title=team_title,
            team_subtitle=team_subtitle,
            logo_url=logo.filename if logo else None,
            target_market=target_market,
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
        # Handle multiple image uploads
        if uploaded_images:
            for image in uploaded_images:
                if image and image.filename:  # Check if the file is valid
                    try:
                        image_url = upload_picture_for_web_page(image)  # Assuming upload_picture returns a URL
                        new_photo = WebpageMedia(
                            micro_webpage=new_micropage,
                            micro_webpage_id=new_micropage.id,
                            picture_url=image_url,
                            press_kit_url=None
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
