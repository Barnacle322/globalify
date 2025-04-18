import json

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    url_for,
)

from .main import bad_request
from ..extensions import db
from ..models import ( Company)
from ..models.microwebpage import MicroWebPage, WebpageMedia, WebpageCompanyCustomer, WebpageCompanyEmployee
from ..utils.google_helpers.google_storage import upload_picture, upload_picture_for_web_page

microwebpage = Blueprint("micropage", __name__)




@microwebpage.get("/webpage/<int:microwebpage_id>")
def get_micro_web_page(microwebpage_id):
    micro_web_page = MicroWebPage.get_by_id(microwebpage_id)
    company = micro_web_page.company
    return render_template("microwebpage/micro_web_page.html", microwebpage=micro_web_page, company=company)


@microwebpage.route("/get/data/<int:microwebpage_id>", methods=["GET"])
def get_micro_web_page_data(microwebpage_id):
    microwebpage = MicroWebPage.get_by_id(microwebpage_id)
    if not microwebpage:
        return jsonify({"error": "MicroWebPage not found"}), 404

    data = {
        "id": microwebpage.id,
        "company_id": microwebpage.company_id,
        "hero_title": microwebpage.hero_title,
        "hero_subtitle": microwebpage.hero_subtitle,
        "logo_url": microwebpage.logo_url,
        "logo_cloud_title": microwebpage.logo_cloud_title,
        "benefit_title": microwebpage.benefit_title,
        "benefit_subtitle": microwebpage.benefit_subtitle,
        "benefit_statement": microwebpage.benefit_statement,
        "stat_title": microwebpage.stat_title,
        "stat_subtitle": microwebpage.stat_subtitle,
        "statistics": microwebpage.statistics,
        "mission_title": microwebpage.mission_title,
        "mission_statement": microwebpage.mission_statement,
        "leadership_title": microwebpage.leadership_title,
        "leadership_subtitle": microwebpage.leadership_subtitle,
        "faq_title": microwebpage.faq_title,
        "faq": microwebpage.faq,
        "about_title": microwebpage.about_title,
        "about_subtitle": microwebpage.about_subtitle,
        "about_statement": microwebpage.about_statement,
        "values_title": microwebpage.values_title,
        "values_subtitle": microwebpage.values_subtitle,
        "values_statement": microwebpage.values_statement,
        "customer_testimonials_title": microwebpage.customer_testimonials_title,
        "customer_testimonials_subtitle": microwebpage.customer_testimonials_subtitle,
        "images": [
            {"id": media.id, "picture_url": media.picture_url}
            for media in microwebpage.webpage_media
            if media.picture_url
        ],
        "cloud_logos": [
            {"id": media.id, "logo_url": media.logo_url}
            for media in microwebpage.webpage_media
            if media.logo_url
        ],
        "employees": [
            {
                "id": emp.id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "position": emp.position,
                "picture_url": emp.picture_url,
                "bio": emp.bio
            }
            for emp in microwebpage.employees
        ],
        "customers": [
            {
                "id": cust.id,
                "first_name": cust.first_name,
                "last_name": cust.last_name,
                "position": cust.position,
                "picture_url": cust.picture_url,
                "feedback": cust.feedback
            }
            for cust in microwebpage.customers
        ]
    }
    return jsonify(data), 200



@microwebpage.route("/create/<int:company_id>", methods=["GET", "POST"])
def get_or_create_micro_web_page(company_id):
    company = Company.get_by_id(company_id)
    webpage = MicroWebPage.get_by_id(company_id)
    if not company:
        return jsonify({"error": "Company does not exist!"}), 400
    if company.microwebpage and not webpage.is_published:
            return bad_request(400)
    if company.microwebpage:
        return render_template("microwebpage/micro_web_page.html", microwebpage=company.microwebpage, company=company)

    if request.method == "POST":
        required_fields = {
            "hero_title": "Hero title is required",
            "hero_subtitle": "Hero subtitle is required",
        }

        form_data = {}
        for field, error_msg in required_fields.items():
            value = request.form.get(field)
            if not value:
                return jsonify({"error": error_msg}), 400
            form_data[field] = value

        # File uploads
        uploaded_images = request.files.getlist("images[]")
        logo = request.files.get("logo")
        cloud_logos = request.files.getlist("cloud_logos[]")

        logo_cloud_title = request.form.get("logo_cloud_title")
        benefit_title = request.form.get("benefit_title")
        benefit_subtitle = request.form.get("benefit_subtitle")
        benefit_statement_json = request.form.get("benefit_statement")
        stat_title = request.form.get("stat_title")
        stat_subtitle = request.form.get("stat_subtitle")
        statistics_json = request.form.get("statistics")
        mission_title = request.form.get("mission_title")
        mission_statement = request.form.get("mission_statement")
        leadership_title = request.form.get("leadership_title")
        leadership_subtitle = request.form.get("leadership_subtitle")
        customer_testimonials_title = request.form.get("customer_testimonials_title")
        customer_testimonials_subtitle = request.form.get("customer_testimonials_subtitle")
        faq_title = request.form.get("faq_title")
        faq_json = request.form.get("faq")
        about_title = request.form.get("about_title")
        about_subtitle = request.form.get("about_subtitle")
        about_statement_json = request.form.get("about_statement")
        values_title = request.form.get("values_title")
        values_subtitle = request.form.get("values_subtitle")
        values_statement_json = request.form.get("values_statement")

        # Parse JSON fields if they exist
        benefit_statement = json.loads(benefit_statement_json) if benefit_statement_json else None
        statistics = json.loads(statistics_json) if statistics_json else None
        faq = json.loads(faq_json) if faq_json else None
        about_statement = json.loads(about_statement_json) if about_statement_json else None
        values_statement = json.loads(values_statement_json) if values_statement_json else None

        employees_data = []
        customers_data = []

        # Extract employees from form data
        employee_keys = [key for key in request.form.keys() if key.startswith("employees[")]
        if employee_keys:
            # Group by index (e.g., employees[0], employees[1])
            employee_indices = sorted(set(key.split('[')[1].split(']')[0] for key in employee_keys))
            for index in employee_indices:
                prefix = f"employees[{index}]"
                first_name = request.form.get(f"{prefix}[first_name]", "")
                if first_name:  # Only process if first_name exists
                    employee_data = {
                        "first_name": first_name,
                        "last_name": request.form.get(f"{prefix}[last_name]", ""),
                        "position": request.form.get(f"{prefix}[position]", ""),
                        "bio": request.form.get(f"{prefix}[bio]", ""),
                        "picture": request.files.get(f"{prefix}[picture]")
                    }
                    employees_data.append(employee_data)

        # Extract customers from form data
        customer_keys = [key for key in request.form.keys() if key.startswith("customers[")]
        if customer_keys:
            # Group by index (e.g., customers[0], customers[1])
            customer_indices = sorted(set(key.split('[')[1].split(']')[0] for key in customer_keys))
            for index in customer_indices:
                prefix = f"customers[{index}]"
                first_name = request.form.get(f"{prefix}[first_name]", "")
                if first_name:  # Only process if first_name exists
                    customer_data = {
                        "first_name": first_name,
                        "last_name": request.form.get(f"{prefix}[last_name]", ""),
                        "position": request.form.get(f"{prefix}[position]", ""),
                        "feedback": request.form.get(f"{prefix}[feedback]", ""),
                        "picture": request.files.get(f"{prefix}[picture]")
                    }
                    customers_data.append(customer_data)

        # Create new MicroWebPage instance
        new_micropage = MicroWebPage(
            company=company,
            company_id=company_id,
            logo_url=None,
            hero_title=form_data["hero_title"],
            hero_subtitle=form_data["hero_subtitle"],
            logo_cloud_title=logo_cloud_title,
            benefit_title=benefit_title,
            benefit_subtitle=benefit_subtitle,
            benefit_statement=benefit_statement,
            stat_title=stat_title,
            stat_subtitle=stat_subtitle,
            statistics=statistics,
            mission_title=mission_title,
            mission_statement=mission_statement,
            leadership_title=leadership_title,
            leadership_subtitle=leadership_subtitle,
            customer_testimonials_title=customer_testimonials_title,
            customer_testimonials_subtitle=customer_testimonials_subtitle,
            faq_title=faq_title,
            faq=faq,
            about_title=about_title,
            about_subtitle=about_subtitle,
            about_statement=about_statement,
            values_title=values_title,
            values_subtitle=values_subtitle,
            values_statement=values_statement
        )

        db.session.add(new_micropage)
        db.session.flush()

        # Handle primary logo upload
        if logo and logo.filename:
            try:
                logo_url = upload_picture(logo)
                new_micropage.logo_url = logo_url
            except Exception as e:
                print(f"Error uploading primary logo: {str(e)}")

        # Handle cloud logos upload
        if cloud_logos:
            for cloud_logo in cloud_logos:
                if cloud_logo and cloud_logo.filename:
                    try:
                        logo_url = upload_picture(cloud_logo)
                        new_media = WebpageMedia(
                            micro_webpage=new_micropage,
                            micro_webpage_id=new_micropage.id,
                            press_kit_url=None,
                            picture_url=None,
                            logo_url=logo_url
                        )
                        db.session.add(new_media)
                    except Exception as e:
                        print(f"Error uploading cloud logo: {str(e)}")
                        continue

        # Handle multiple image uploads
        if uploaded_images:
            for image in uploaded_images:
                if image and image.filename:
                    try:
                        image_url = upload_picture_for_web_page(image)
                        new_media = WebpageMedia(
                            micro_webpage=new_micropage,
                            micro_webpage_id=new_micropage.id,
                            press_kit_url=None,
                            picture_url=image_url,
                            logo_url=None
                        )
                        db.session.add(new_media)
                    except Exception as e:
                        print(f"Error uploading image: {str(e)}")
                        continue

        # Handle employee uploads
        for employee in employees_data:
            picture_url = None
            if employee["picture"] and employee["picture"].filename:
                try:
                    picture_url = upload_picture(employee["picture"])
                except Exception as e:
                    print(f"Error uploading employee picture: {str(e)}")
                    continue
            new_employee = WebpageCompanyEmployee(
                micro_webpage=new_micropage,
                micro_webpage_id=new_micropage.id,
                first_name=employee["first_name"],
                last_name=employee["last_name"],
                position=employee["position"],
                picture_url=picture_url,
                bio=employee["bio"]
            )
            db.session.add(new_employee)

        # Handle customer uploads
        for customer in customers_data:
            picture_url = None
            if customer["picture"] and customer["picture"].filename:
                try:
                    picture_url = upload_picture(customer["picture"])
                except Exception as e:
                    print(f"Error uploading customer picture: {str(e)}")
                    continue
            new_customer = WebpageCompanyCustomer(
                micro_webpage=new_micropage,
                micro_webpage_id=new_micropage.id,
                first_name=customer["first_name"],
                last_name=customer["last_name"],
                position=customer["position"],
                picture_url=picture_url,
                feedback=customer["feedback"]
            )
            db.session.add(new_customer)

        db.session.commit()

        return jsonify({
            "redirect_url": url_for("micropage.get_micro_web_page", microwebpage_id=new_micropage.id)
        }), 200

    return render_template("microwebpage/create_micro_web_page.html", company=company)


@microwebpage.route("/update/<int:microwebpage_id>", methods=["GET", "POST"])
def update_micro_web_page(microwebpage_id):
    print("Hello World from update")
    microwebpage = MicroWebPage.get_by_id(microwebpage_id)
    if not microwebpage:
        return jsonify({"error": "MicroWebPage does not exist!"}), 404
    company = microwebpage.company

    if request.method == "POST":
        required_fields = {
            "hero_title": "Hero title is required",
            "hero_subtitle": "Hero subtitle is required",
        }

        form_data = {}
        for field, error_msg in required_fields.items():
            value = request.form.get(field)
            if not value:
                return jsonify({"error": error_msg}), 400
            form_data[field] = value

        # File uploads
        uploaded_images = request.files.getlist("images[]")
        logo = request.files.get("logo")
        cloud_logos = request.files.getlist("cloud_logos[]")

        # Scalar fields
        logo_cloud_title = request.form.get("logo_cloud_title")
        benefit_title = request.form.get("benefit_title")
        benefit_subtitle = request.form.get("benefit_subtitle")
        benefit_statement_json = request.form.get("benefit_statement")
        stat_title = request.form.get("stat_title")
        stat_subtitle = request.form.get("stat_subtitle")
        statistics_json = request.form.get("statistics")
        mission_title = request.form.get("mission_title")
        mission_statement = request.form.get("mission_statement")
        leadership_title = request.form.get("leadership_title")
        leadership_subtitle = request.form.get("leadership_subtitle")
        customer_testimonials_title = request.form.get("customer_testimonials_title")
        customer_testimonials_subtitle = request.form.get("customer_testimonials_subtitle")
        faq_title = request.form.get("faq_title")
        faq_json = request.form.get("faq")
        about_title = request.form.get("about_title")
        about_subtitle = request.form.get("about_subtitle")
        about_statement_json = request.form.get("about_statement")
        values_title = request.form.get("values_title")
        values_subtitle = request.form.get("values_subtitle")
        values_statement_json = request.form.get("values_statement")

        # Parse JSON fields
        benefit_statement = json.loads(benefit_statement_json) if benefit_statement_json else []
        statistics = json.loads(statistics_json) if statistics_json else []
        faq = json.loads(faq_json) if faq_json else []
        about_statement = json.loads(about_statement_json) if about_statement_json else []
        values_statement = json.loads(values_statement_json) if values_statement_json else []

        # Extract employees
        employees_data = []
        employee_keys = [key for key in request.form.keys() if key.startswith("employees[")]
        if employee_keys:
            employee_indices = sorted(set(key.split('[')[1].split(']')[0] for key in employee_keys))
            for index in employee_indices:
                prefix = f"employees[{index}]"
                first_name = request.form.get(f"{prefix}[first_name]", "")
                employee_id = request.form.get(f"{prefix}[id]")
                if first_name:
                    employee_data = {
                        "id": int(employee_id) if employee_id else None,
                        "first_name": first_name,
                        "last_name": request.form.get(f"{prefix}[last_name]", ""),
                        "position": request.form.get(f"{prefix}[position]", ""),
                        "bio": request.form.get(f"{prefix}[bio]", ""),
                        "picture": request.files.get(f"{prefix}[picture]")
                    }
                    employees_data.append(employee_data)

        # Extract customers
        customers_data = []
        customer_keys = [key for key in request.form.keys() if key.startswith("customers[")]
        if customer_keys:
            customer_indices = sorted(set(key.split('[')[1].split(']')[0] for key in customer_keys))
            for index in customer_indices:
                prefix = f"customers[{index}]"
                first_name = request.form.get(f"{prefix}[first_name]", "")
                customer_id = request.form.get(f"{prefix}[id]")
                if first_name:
                    customer_data = {
                        "id": int(customer_id) if customer_id else None,
                        "first_name": first_name,
                        "last_name": request.form.get(f"{prefix}[last_name]", ""),
                        "position": request.form.get(f"{prefix}[position]", ""),
                        "feedback": request.form.get(f"{prefix}[feedback]", ""),
                        "picture": request.files.get(f"{prefix}[picture]")
                    }
                    customers_data.append(customer_data)

        try:
            # Update MicroWebPage
            microwebpage.hero_title = form_data["hero_title"]
            microwebpage.hero_subtitle = form_data["hero_subtitle"]
            microwebpage.logo_cloud_title = logo_cloud_title
            microwebpage.benefit_title = benefit_title
            microwebpage.benefit_subtitle = benefit_subtitle
            microwebpage.benefit_statement = benefit_statement
            microwebpage.stat_title = stat_title
            microwebpage.stat_subtitle = stat_subtitle
            microwebpage.statistics = statistics
            microwebpage.mission_title = mission_title
            microwebpage.mission_statement = mission_statement
            microwebpage.leadership_title = leadership_title
            microwebpage.leadership_subtitle = leadership_subtitle
            microwebpage.customer_testimonials_title = customer_testimonials_title
            microwebpage.customer_testimonials_subtitle = customer_testimonials_subtitle
            microwebpage.faq_title = faq_title
            microwebpage.faq = faq
            microwebpage.about_title = about_title
            microwebpage.about_subtitle = about_subtitle
            microwebpage.about_statement = about_statement
            microwebpage.values_title = values_title
            microwebpage.values_subtitle = values_subtitle
            microwebpage.values_statement = values_statement

            # Handle primary logo upload
            if logo and logo.filename:
                try:
                    logo_url = upload_picture(logo)
                    microwebpage.logo_url = logo_url
                except Exception as e:
                    print(f"Error uploading primary logo: {str(e)}")

            # Handle cloud logos (update or create)
            if cloud_logos:
                existing_cloud_logos = {
                    media.id: media
                    for media in microwebpage.webpage_media
                    if media.logo_url
                }
                new_cloud_logos = []
                for index, cloud_logo in enumerate(cloud_logos):
                    cloud_logo_id = request.form.get(f"cloud_logos[{index}][id]")
                    if cloud_logo and cloud_logo.filename:
                        new_cloud_logos.append({
                            "id": int(cloud_logo_id) if cloud_logo_id else None,
                            "file": cloud_logo
                        })

                for cloud_logo_data in new_cloud_logos:
                    cloud_logo_id = cloud_logo_data["id"]
                    try:
                        logo_url = upload_picture(cloud_logo_data["file"])
                    except Exception as e:
                        print(f"Error uploading cloud logo: {str(e)}")
                        continue

                    if cloud_logo_id and cloud_logo_id in existing_cloud_logos:
                        media = existing_cloud_logos[cloud_logo_id]
                        media.logo_url = logo_url
                    else:
                        new_media = WebpageMedia(
                            micro_webpage_id=microwebpage.id,
                            press_kit_url=None,
                            picture_url=None,
                            logo_url=logo_url
                        )
                        db.session.add(new_media)

                submitted_cloud_logo_ids = {cl["id"] for cl in new_cloud_logos if cl["id"]}
                for media_id, media in existing_cloud_logos.items():
                    if media_id not in submitted_cloud_logo_ids:
                        db.session.delete(media)

            # Handle images (update or create)
            existing_images = {
                media.id: media
                for media in microwebpage.webpage_media
                if media.picture_url
            }
            new_images = []
            deleted_image_ids = [
                int(id) for id in request.form.getlist("deleted_images[]") if id
            ]
            submitted_image_ids = {
                int(id) for id in request.form.getlist("images_ids[]") if id
            }

            print(f"Submitted image IDs: {submitted_image_ids}")
            print(f"Deleted image IDs: {deleted_image_ids}")

            for image in uploaded_images:
                if image and image.filename:
                    new_images.append({
                        "id": None,
                        "file": image
                    })

            # Validate at least one image remains
            if not new_images and not submitted_image_ids:
                return jsonify({"error": "At least one company photo is required"}), 400

            for image_data in new_images:
                try:
                    image_url = upload_picture_for_web_page(image_data["file"])
                except Exception as e:
                    print(f"Error uploading image: {str(e)}")
                    continue

                new_media = WebpageMedia(
                    micro_webpage=microwebpage,
                    micro_webpage_id=microwebpage.id,
                    press_kit_url=None,
                    picture_url=image_url,
                    logo_url=None
                )
                db.session.add(new_media)

            for media_id, media in existing_images.items():
                if media_id not in submitted_image_ids or media_id in deleted_image_ids:
                    db.session.delete(media)

            # Handle employees (update or create)
            if employees_data:
                existing_employees = {
                    emp.id: emp
                    for emp in microwebpage.employees
                }
                for employee_data in employees_data:
                    employee_id = employee_data["id"]
                    picture_url = None
                    if employee_data["picture"] and employee_data["picture"].filename:
                        try:
                            picture_url = upload_picture(employee_data["picture"])
                        except Exception as e:
                            print(f"Error uploading employee picture: {str(e)}")
                            continue

                    if employee_id and employee_id in existing_employees:
                        employee = existing_employees[employee_id]
                        employee.first_name = employee_data["first_name"]
                        employee.last_name = employee_data["last_name"]
                        employee.position = employee_data["position"]
                        employee.bio = employee_data["bio"]
                        if picture_url:
                            employee.picture_url = picture_url
                    else:
                        new_employee = WebpageCompanyEmployee(
                            micro_webpage=microwebpage,
                            micro_webpage_id=microwebpage.id,
                            first_name=employee_data["first_name"],
                            last_name=employee_data["last_name"],
                            position=employee_data["position"],
                            picture_url=picture_url,
                            bio=employee_data["bio"]
                        )
                        db.session.add(new_employee)

                submitted_employee_ids = {emp["id"] for emp in employees_data if emp["id"]}
                for emp_id, emp in existing_employees.items():
                    if emp_id not in submitted_employee_ids:
                        db.session.delete(emp)

            # Handle customers (update or create)
            if customers_data:
                existing_customers = {
                    cust.id: cust
                    for cust in microwebpage.customers
                }
                for customer_data in customers_data:
                    customer_id = customer_data["id"]
                    picture_url = None
                    if customer_data["picture"] and customer_data["picture"].filename:
                        try:
                            picture_url = upload_picture(customer_data["picture"])
                        except Exception as e:
                            print(f"Error uploading customer picture: {str(e)}")
                            continue

                    if customer_id and customer_id in existing_customers:
                        customer = existing_customers[customer_id]
                        customer.first_name = customer_data["first_name"]
                        customer.last_name = customer_data["last_name"]
                        customer.position = customer_data["position"]
                        customer.feedback = customer_data["feedback"]
                        if picture_url:
                            customer.picture_url = picture_url
                    else:
                        new_customer = WebpageCompanyCustomer(
                            micro_webpage=microwebpage,
                            micro_webpage_id=microwebpage.id,
                            first_name=customer_data["first_name"],
                            last_name=customer_data["last_name"],
                            position=customer_data["position"],
                            picture_url=picture_url,
                            feedback=customer_data["feedback"]
                        )
                        db.session.add(new_customer)

                submitted_customer_ids = {cust["id"] for cust in customers_data if cust["id"]}
                for cust_id, cust in existing_customers.items():
                    if cust_id not in submitted_customer_ids:
                        db.session.delete(cust)

            db.session.commit()

            return jsonify({
                "redirect_url": url_for("micropage.get_micro_web_page", microwebpage_id=microwebpage.id)
            }), 200

        except Exception as e:
            db.session.rollback()
            print(f"Error during update: {str(e)}")
            return jsonify({"error": "Failed to update MicroWebPage"}), 500

    return render_template("microwebpage/create_micro_web_page.html", company=company, microwebpage=microwebpage)


@microwebpage.get("/about/<int:company_id>")
def about_micro_web_page(company_id):
    microwebpage = MicroWebPage.get_by_id(company_id)
    company = microwebpage.company
    return render_template("microwebpage/about.html", company=company, microwebpage=microwebpage)



@microwebpage.route("/publish/<int:microwebpage_id>", methods=["POST"])
def toggle_publish(microwebpage_id):
    microwebpage = MicroWebPage.get_by_id(microwebpage_id)
    data = request.get_json()
    if data is None or 'is_published' not in data:
        return jsonify({"error": "Missing is_published parameter"}), 400

    is_published = data['is_published']
    microwebpage.is_published = is_published
    try:
        db.session.commit()
        return jsonify({"message": f"MicroWebPage {'published' if is_published else 'unpublished'} successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to update publish status: {str(e)}"}), 500



