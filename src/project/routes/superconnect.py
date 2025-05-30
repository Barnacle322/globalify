import os
from datetime import UTC, datetime, timedelta

import stripe
from flask import (
    Blueprint,
    json,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from src.project.models.user import Company

from ..extensions import db
from ..models import User
from ..models.superconnect import (
    Expert,
    Qualification,
    QualificationType,
    SessionRequest,
    SessionStatus,
)
from ..schemas.superconnect import ExpertSchema, QualificationSchema, SessionSchema
from ..utils.decorators import (
    check_user_info_complete,
    check_verification,
)
from ..utils.enums import SessionType, Status, StatusType
from ..utils.errors.error_messages import PICTURE_NOT_LOADED
from ..utils.google_helpers.google_storage import upload_picture
from ..utils.scraper import add_https_prefix
from ..utils.stripe import get_or_create_stripe_price, get_or_create_stripe_product

superconnect = Blueprint("superconnect", __name__)


@superconnect.route("/api/experts")
@check_user_info_complete
@check_verification
def api_experts():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 9, type=int)

    expertise = request.args.get("expertise", "All")
    print("Agahan", expertise)
    region = request.args.get("region", "Worldwide")
    search_query = request.args.get("search", "")

    query = Expert.query

    if expertise != "All":
        print("Agahan2", expertise)
        query = query.join(Expert.qualifications).filter(Qualification.type == expertise)

    if region != "Worldwide":
        query = query.join(Expert.user).join(User.user_info).filter(User.user_info.country == region)

    if search_query:
        from ..models import UserInfo

        query = (
            query.join(Expert.user)
            .join(User.user_info)
            .filter(
                db.or_(
                    UserInfo.first_name.ilike(f"%{search_query}%"),
                    UserInfo.last_name.ilike(f"%{search_query}%"),
                    Expert.bio.ilike(f"%{search_query}%"),
                )
            )
        )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    experts_data = []
    for expert in pagination.items:
        expert_data = {
            "id": expert.id,
            "name": f"{expert.first_name} {expert.last_name}",
            "picture_url": expert.picture_url,
            "bio": expert.bio or "This expert helps businesses expand globally.",
            "position": expert.position,
            "experience_years": len(expert.qualifications) if expert.qualifications else 0,
            "qualifications": [{"id": q.id, "type": q.type.value, "title": q.title} for q in expert.qualifications][:3],
        }
        experts_data.append(expert_data)

    pagination_meta = {
        "page": page,
        "per_page": per_page,
        "total": pagination.total,
        "pages": pagination.pages,
        "has_next": pagination.has_next,
        "has_prev": pagination.has_prev,
        "next_num": pagination.next_num if pagination.has_next else None,
        "prev_num": pagination.prev_num if pagination.has_prev else None,
    }

    return jsonify(
        {
            "experts": experts_data,
            "pagination": pagination_meta,
            "filters": {"expertise": expertise, "region": region, "search": search_query},
        }
    )


@superconnect.route("/api/qualification-types", methods=["GET"])
@check_user_info_complete
@check_verification
def get_qualification_types():
    types = [{"value": typ.name, "name": typ.value.capitalize()} for typ in QualificationType]

    return jsonify({"qualification_types": types})


@superconnect.route("/list", methods=["GET"])
@check_user_info_complete
@check_verification
def index():
    return render_template("superconnect/index.html", current_user=current_user)


@superconnect.route("/profile", methods=["GET"])
@check_user_info_complete
@check_verification
def profile():
    status_type, msg = None, None
    if query := request.args:
        status_type = query.get("type")
        msg = query.get("msg")

    expert = Expert.get_by_id(current_user.expert.id)
    if not expert:
        return jsonify({"error": "Expert not found"}), 404
    qualification_types = [qt.value for qt in QualificationType]

    return render_template(
        "superconnect/profile.html",
        expert=expert,
        qualificationTypes=qualification_types,
        status_type=status_type,
        msg=msg,
    )


@superconnect.get("/get/<expert_id>")
@check_user_info_complete
@check_verification
def get_expert_by_id(expert_id):
    expert = Expert.get_by_id(expert_id)
    if not expert:
        return jsonify({"error": "Expert not found"}), 404

    # Сериализация данных через Pydantic-схему
    expert_data = ExpertSchema(
        id=expert.id,
        name=expert.full_name,
        user_id=expert.user_id,
        bio=expert.bio,
        description=expert.description,
        picture_url=expert.picture_url,
        position=expert.position,
        linkedin=expert.linkedin,
        twitter=expert.twitter,
        email=expert.email,
        phone_number=expert.phone_number,
        location=expert.location,
        price=expert.price,
        qualifications=[
            QualificationSchema(
                id=q.id,
                type=q.type.value,
                title=q.title,
                description=q.description,
                company_id=q.company_id if q.company_id else None,
                company_name=q.company_name,
                company_description=q.company_description,
                company_url=q.company_url,
                start_date=q.start_date,
                end_date=q.end_date,
            )
            for q in expert.qualifications
        ],
    )

    # Преобразование Pydantic-объекта в словарь
    return jsonify({"expert": expert_data.model_dump()})


def create_payment_intent(expert, user, session_type, notes):
    """Создает PaymentIntent с manual capture"""
    stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")

    return stripe.PaymentIntent.create(
        amount=int(expert.price * 100),
        currency="usd",
        capture_method="manual",
        metadata={
            "expert_id": str(expert.id),
            "user_id": str(user.id),
            "session_type": session_type,
            "notes": notes,
        },
    )


# @superconnect.post("/stripe-webhook")
# def stripe_webhook():
#     payload = request.get_data(as_text=True)
#     sig_header = request.headers.get("Stripe-Signature")
#     webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

#     try:
#         event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
#     except ValueError as e:
#         return jsonify({"error": "Invalid payload"}), 400
#     except stripe.error.SignatureVerificationError as e:
#         return jsonify({"error": "Invalid signature"}), 400

#     # Логирование всех событий
#     print(f"Webhook event received: {event.type}")

#     # Обработка различных событий
#     if event.type == "invoice.sent":
#         invoice = event.data.object
#         print(f"Invoice {invoice.id} sent to {invoice.customer_email}")

#     if event.type == "invoice.payment_succeeded":
#         invoice = event.data.object
#         session_request_id = invoice.metadata.get("session_request_id")
#         if session_request_id:
#             session_request = SessionRequest.get_by_id(int(session_request_id))
#             if session_request:
#                 session_request.status = SessionStatus.PENDING
#                 session_request.payment_date = datetime.now(UTC)
#                 session_request.paid_amount = invoice.amount_paid / 100
#                 db.session.commit()

#     return jsonify({"status": "success"}), 200


@superconnect.post("/book-session/<int:expert_id>")
@check_user_info_complete
@check_verification
def book_session(expert_id):
    expert = Expert.get_by_id(expert_id)
    if not expert:
        return jsonify({"success": False, "error": "Expert not found"}), 404

    if not expert.price or expert.price <= 0:
        return jsonify({"success": False, "error": "This expert doesn't have a session price set"}), 400

    form_data = request.get_json()
    notes = form_data.get("notes", "")
    session_type = form_data.get("session_type", "consultation")

    try:
        session_request = SessionRequest(
            user_id=current_user.id,
            expert_id=expert.id,
            notes=notes,
            type=SessionType(session_type),
            status=SessionStatus.PENDING,
        )
        db.session.add(session_request)
        db.session.flush()

        stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")

        customers = stripe.Customer.list(email=current_user.email, limit=1)
        if customers.data:
            customer = customers.data[0]
        else:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.user_info.full_name if hasattr(current_user, "user_info") else current_user.email,
                metadata={"user_id": str(current_user.id)},
            )

        print(f"Stripe customer created or retrieved: {customer.id}")

        product_id = get_or_create_stripe_product(expert)

        print(f"Stripe product created or retrieved: {product_id}")

        price = stripe.Price.create(
            unit_amount=int(expert.price * 100),
            currency="usd",
            product=product_id,
        )

        print(f"Stripe price created: {price.id}")
        invoice = stripe.Invoice.create(
            customer=customer.id,
            collection_method="send_invoice",
            days_until_due=7,
        )

        invoice_item = stripe.InvoiceItem.create(
            customer=customer.id,
            price=price.id,
            quantity=1,
            invoice=invoice.id,  # type: ignore
            description=f"Consultation with {expert.full_name}",
        )

        stripe.Invoice.send_invoice(invoice.id)  # type: ignore

        print(f"Stripe invoice created: {invoice.id}")
        print(f"Invoice hosted URL: {invoice}")

        session_request.stripe_session_id = str(invoice.id)
        db.session.commit()

        # 8. Возвращаем успешный ответ с URL просмотра счета
        return jsonify(
            {
                "success": True,
                "message": "Session request has been created. Payment invoice has been sent to your email.",
                "invoice_url": "https://dashboard.stripe.com/invoices/" + invoice.id,  # type: ignore
            }
        )

    except Exception as e:
        db.session.rollback()
        print(f"Error creating session request: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@superconnect.get("/checkout-success/<int:session_request_id>")
@check_user_info_complete
@check_verification
def checkout_success(session_request_id):
    session_request = SessionRequest.get_by_id(session_request_id)
    if not session_request:
        print("Session request not found", "error")
        return redirect(url_for("superconnect.expert_list"))

    session_id = request.args.get("session_id")
    if not session_id:
        print("Invalid checkout session", "error")
        return redirect(url_for("superconnect.expert_list"))

    try:
        stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")
        checkout_session = stripe.checkout.Session.retrieve(
            session_id,
            expand=["payment_intent"],
        )

        print("Checkout session:", checkout_session)

        if checkout_session.payment_status == "paid":
            payment_intent = checkout_session.payment_intent
            if isinstance(payment_intent, stripe.PaymentIntent) and hasattr(payment_intent, "id"):
                session_request.stripe_payment_intent_id = payment_intent.id
            else:
                raise ValueError("Invalid payment_intent object or missing 'id' attribute")

            if isinstance(payment_intent, stripe.PaymentIntent) and hasattr(payment_intent, "amount"):
                session_request.paid_amount = payment_intent.amount / 100  # конвертируем центы в доллары
            else:
                raise ValueError("Invalid payment_intent object or missing 'amount' attribute")
            session_request.payment_date = datetime.now(UTC)

            db.session.commit()

            print("Payment successful! Your session request has been sent to the expert.", "success")
        else:
            print("Payment is pending or incomplete. Please check your payment status.", "warning")

    except Exception as e:
        print(f"Error processing checkout success: {e}")
        print("Error processing your payment. Please contact support.", "error")

    return redirect(url_for("superconnect.user_sessions"))


@superconnect.get("/checkout-cancel/<int:session_request_id>")
@check_user_info_complete
@check_verification
def checkout_cancel(session_request_id):
    session_request = SessionRequest.get_by_id(session_request_id)
    if session_request:
        session_request.status = SessionStatus.CANCELED
        db.session.commit()

    return redirect(url_for("superconnect.expert_list"))


@superconnect.post("/session/action/")
@check_user_info_complete
@check_verification
def change_session_status():
    form_data = request.get_json()
    session_id = form_data.get("session_id")
    action = form_data.get("action")

    if not session_id or not action:
        return jsonify({"error": "Missing required parameters"}), 400

    session = SessionRequest.get_by_id(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404

    if session.expert_id != current_user.id:
        return jsonify({"error": "Access denied"}), 403

    if action == SessionStatus.UPCOMING.value:
        try:
            if session.status != SessionStatus.PENDING:
                return jsonify({"error": "Session cannot be modified"}), 400

            if session.stripe_payment_intent_id:
                payment_intent = stripe.PaymentIntent.retrieve(session.stripe_payment_intent_id)
                try:
                    payment_intent = stripe.PaymentIntent.retrieve(session.stripe_payment_intent_id)
                    print("Payment intent status:", payment_intent.status)

                    if payment_intent.status == "succeeded":
                        session.status = SessionStatus.UPCOMING
                    elif payment_intent.status == "canceled":
                        return jsonify({"error": "Payment was canceled"}), 400
                    elif payment_intent.status == "requires_payment_method":
                        return jsonify(
                            {"error": "Payment not completed. The client needs to complete payment first."}
                        ), 400
                    elif payment_intent.status == "requires_confirmation":
                        payment_intent = stripe.PaymentIntent.confirm(session.stripe_payment_intent_id)

                    if payment_intent.status == "requires_capture":
                        stripe.PaymentIntent.capture(session.stripe_payment_intent_id)
                    elif payment_intent.status != "succeeded":
                        return jsonify({"error": f"Payment cannot be captured in status: {payment_intent.status}"}), 400

                except stripe.error.StripeError as e:  # type: ignore
                    print(f"Invalid request error with payment intent: {e}")
        except Exception as e:
            print(f"Capture error: {str(e)}")
            return jsonify({"error": f"Capture failed: {str(e)}"}), 400
    elif action == SessionStatus.CANCELED.value:
        if session.status != SessionStatus.PENDING:
            return jsonify({"error": "Session cannot be modified"}), 400

        if session.stripe_payment_intent_id:
            try:
                stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")

                payment_intent = stripe.PaymentIntent.retrieve(session.stripe_payment_intent_id)

                if payment_intent.status == "succeeded":
                    refund = stripe.Refund.create(
                        payment_intent=session.stripe_payment_intent_id, reason="requested_by_customer"
                    )
                    print(f"Refund created: {refund.id}")
                    session.refund_id = refund.id

                elif payment_intent.status == "requires_capture":
                    stripe.PaymentIntent.cancel(session.stripe_payment_intent_id)
                    print(f"Payment intent canceled: {session.stripe_payment_intent_id}")

                session.status = SessionStatus.CANCELED
                session.canceled_at = datetime.now(UTC)
                session.canceled_by = "expert"

            except Exception as e:
                print(f"Error processing refund: {e}")
                return jsonify({"error": f"Failed to process refund: {str(e)}"}), 500
        else:
            session.status = SessionStatus.CANCELED
            session.canceled_at = datetime.now(UTC)
            session.canceled_by = "expert"

    db.session.commit()
    return jsonify({"message": "Session status updated"}), 200


@superconnect.get("/sessions/")
@check_user_info_complete
@check_verification
def user_sessions():
    return render_template("superconnect/sessions.html", current_user=current_user)


@superconnect.get("/get_sessions/")
@check_user_info_complete
@check_verification
def get_user_sessions():
    print(current_user.id)
    user = User.get_by_id(current_user.id)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if not user.is_expert:
        session_requests = SessionRequest.get_all_by_user_id(current_user.id)
    else:
        expert = Expert.get_by_user_id(current_user.id)
        if not expert:
            return jsonify({"error": "Expert not found"}), 404
        session_requests = SessionRequest.get_all_by_expert_id(expert.id)

    if session_requests is None:
        return jsonify({"sessions": []})

    session_list = []
    for s_request in session_requests:
        session_data = SessionSchema(
            id=s_request.id,
            expert_name=s_request.expert.full_name,
            expert_email=s_request.expert.email or "",
            user_name=s_request.user.user_info.full_name,
            user_email=s_request.user.email or "",
            expert_picture_url=s_request.expert.picture_url or "",
            user_picture_url=s_request.user.user_info.picture_url or "",
            notes=s_request.notes or "",
            type=s_request.type.value,
            status=s_request.status.value,
            created_at=s_request.created_at,
            paid_amount=s_request.paid_amount,
            refund_id=s_request.refund_id,
            canceled_at=s_request.canceled_at if s_request.canceled_at else None,
            payment_date=s_request.payment_date if s_request.payment_date else None,
        )
        session_list.append(session_data.model_dump())

    return jsonify({"sessions": session_list})


@superconnect.get("/qualifications/<int:expert_id>")
@check_user_info_complete
@check_verification
def get_expert_qualifications(expert_id):
    qualifications = Qualification.get_all_by_expert_id(expert_id)

    if qualifications:
        json_qualifications = [
            {
                "id": q.id,
                "type": q.type.value,
                "title": q.title,
                "start_date": q.start_date.isoformat() if q.start_date else None,
                "end_date": q.end_date.isoformat() if q.end_date else None,
                "description": q.description,
                "company_name": q.company_name,
                "company_url": q.company_url,
            }
            for q in qualifications
        ]
    else:
        json_qualifications = []
    return jsonify(json_qualifications), 200


@superconnect.post("/update/<int:expert_id>")
@check_user_info_complete
@check_verification
def update_expert(expert_id):
    form_data = request.form
    file_data = request.files

    expert = Expert.get_by_id(expert_id)
    if not expert:
        return jsonify({"error": "Expert not found"}), 404

    try:
        first_name = form_data.get("first_name")
        if not first_name:
            return jsonify({"error": "First name is required"}), 400
        expert.first_name = first_name
        expert.last_name = form_data.get("last_name") or None
        expert.firm_name = form_data.get("firm_name") or None
        expert.position = form_data.get("position") or None
        expert.location = form_data.get("location") or None
        expert.bio = form_data.get("bio") or None
        expert.description = form_data.get("description") or None
        expert.linkedin = add_https_prefix(form_data.get("linkedin", "").strip()) if form_data.get("linkedin") else None
        expert.twitter = add_https_prefix(form_data.get("twitter", "").strip()) if form_data.get("twitter") else None
        expert.email = form_data.get("email") or None
        expert.phone_number = form_data.get("phone_number") or None

        price_str = form_data.get("price")
        if price_str and price_str.strip():
            try:
                price = float(price_str)
                if price < 0:
                    return jsonify({"error": "Price cannot be negative"}), 400
                expert.price = price
            except ValueError:
                return jsonify({"error": "Invalid price format"}), 400

        user_email = form_data.get("user_email")
        if user_email:
            user = User.query.filter_by(email=user_email).first()
            if not user:
                return jsonify({"error": "User with provided email does not exist"}), 400
            expert.user_id = user.id
        else:
            expert.user_id = None

        picture = file_data.get("picture")
        if picture:
            try:
                picture_url = upload_picture(picture)
                expert.picture_url = picture_url
            except Exception as e:
                print(e)
                status = Status(StatusType.ERROR, PICTURE_NOT_LOADED).get_status()
                return redirect(url_for("superconnect.profile", expert_id=expert_id, _external=True, **status))

        qualifications_data = json.loads(form_data.get("qualifications", "[]"))
        deleted_ids = json.loads(form_data.get("deleted_qualifications", "[]"))

        if deleted_ids:
            Qualification.delete_by_id_list(deleted_ids)

        for qual_data in qualifications_data:
            qual_id = qual_data.get("id")
            qual_type = qual_data.get("type")
            title = qual_data.get("title")
            description = qual_data.get("description")
            company_id = qual_data.get("company_id")
            company_name = qual_data.get("company_name")
            company_description = qual_data.get("company_description")
            company_url = qual_data.get("company_url")
            start_date_str = qual_data.get("start_date")
            end_date_str = qual_data.get("end_date")

            start_date = datetime.fromisoformat(start_date_str) if start_date_str else None
            end_date = datetime.fromisoformat(end_date_str) if end_date_str else None

            if start_date and end_date and end_date < start_date:
                return jsonify({"error": "Validation error: end_date cannot be before start_date"}), 400

            if not qual_type or not title or not company_name:
                return jsonify({"error": "Qualification type, title, and company name are required"}), 400

            if qual_type not in [qt.value for qt in QualificationType]:
                return jsonify({"error": f"Invalid qualification type: {qual_type}"}), 400

            if qual_id:
                qualification = Qualification.get_by_id(qual_id)
                if not qualification:
                    continue

                qualification.type = QualificationType(qual_type)
                qualification.title = title
                qualification.description = description
                qualification.company_id = company_id
                qualification.company_name = company_name
                qualification.company_description = company_description
                qualification.company_url = add_https_prefix(company_url) if company_url else None
                qualification.start_date = start_date
                qualification.end_date = end_date
                db.session.add(qualification)
            else:
                company = Company.get_by_id(company_id) if company_id else None
                if company:
                    company_name = company.name
                    company_description = company.description
                    company_url = "globalify.xyz/company/" + company.slug
                else:
                    company_url = add_https_prefix(company_url) if company_url else None

                qualification = Qualification(
                    expert_id=expert.id,
                    type=QualificationType(qual_type),
                    title=title,
                    description=description,
                    company_id=company_id,
                    company_name=company_name,
                    company_description=company_description,
                    company_url=company_url,
                    start_date=start_date,
                    end_date=end_date,
                )
                db.session.add(qualification)

        db.session.commit()
        status = Status(StatusType.SUCCESS, "Expert updated successfully!").get_status()
        return redirect(url_for("superconnect.profile", expert_id=expert_id, _external=True, **status))

    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        status = Status(StatusType.ERROR, str(e)).get_status()
        return redirect(url_for("superconnect.profile", expert_id=expert_id, _external=True, **status))
