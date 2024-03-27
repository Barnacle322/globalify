import datetime
import json
import os

import stripe
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from stripe import InvalidRequestError, SignatureVerificationError

from ..extensions import csrf, db
from ..models import Notification, User, UserInfo, UserPayment, WaitlistCharge
from ..utils.enums import ButtonLayout, Events, NotificationDestination, NotificationLayout, Status, StatusType, Tier
from ..utils.errors.error_messages import (
    ONBOARDING_INCOMPLETE,
    PAYMENT_EMAIL_USED,
    PAYMENT_NOT_FOUND,
)
from ..utils.google_helpers import google_pubsub
from .main import check_user_info_complete

payment = Blueprint("payment", __name__)

stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")


def get_invoices(authenticated_user: User):
    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info or not user_info.is_complete:
        raise Exception(ONBOARDING_INCOMPLETE)

    user_payment = UserPayment.get_by_user_id(authenticated_user.id)
    if not user_payment or not user_payment.customer_id:
        waitlist_charge = WaitlistCharge.get_by_customer_email(authenticated_user.email)
        if not waitlist_charge:
            return []
        stripe_invoices = stripe.PaymentIntent.list(customer=waitlist_charge.stripe_customer_id)
        invoices = []
        for stripe_invoice in stripe_invoices:
            invoice = {
                "id": stripe_invoice.get("id"),
                "created": datetime.datetime.fromtimestamp(stripe_invoice.get("created", 0), tz=datetime.UTC).date(),
                "amount_due": stripe_invoice.get("amount"),
                "amount_paid": stripe_invoice.get("amount"),
                "currency": stripe_invoice.get("currency"),
                "status": stripe_invoice.get("status"),
                "hosted_invoice_url": stripe_invoice.get("hosted_invoice_url"),
            }
            invoices.append(invoice)
            return invoices
        return []

    stripe_invoices = stripe.Invoice.list(customer=user_payment.customer_id)
    invoices = []
    for stripe_invoice in stripe_invoices:
        invoice = {
            "id": stripe_invoice.get("id"),
            "created": datetime.datetime.fromtimestamp(stripe_invoice.get("created", 0), tz=datetime.UTC).date(),
            "amount_due": stripe_invoice.get("amount_due"),
            "amount_paid": stripe_invoice.get("amount_paid"),
            "currency": stripe_invoice.get("currency"),
            "status": stripe_invoice.get("status"),
            "hosted_invoice_url": stripe_invoice.get("hosted_invoice_url"),
        }
        invoices.append(invoice)

    return invoices


def handle_customer(authenticated_user: User) -> UserPayment:
    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info or not user_info.is_complete:
        raise Exception(ONBOARDING_INCOMPLETE)

    # Find customer by email
    customer_data = stripe.Customer.search(query=f"email:'{authenticated_user.email}'")
    # If multiple customers are found, raise an exception
    if len(customer_list := customer_data.get("data", [])) > 1:
        raise Exception(PAYMENT_EMAIL_USED)
    # If no customer is found, create a new one
    elif not customer_list:
        stripe_customer = stripe.Customer.create(
            email=authenticated_user.email,
            name=user_info.full_name,
        )
    # If a customer is found, use it
    else:
        stripe_customer = customer_list[0]

    # Find customer in database
    user_payment = UserPayment.get_by_user_id(authenticated_user.id)
    if user_payment:
        stripe_customer_id = stripe_customer.get("id")
        # If customer is found, check if customer_id matches
        if user_payment.customer_id == stripe_customer_id and user_payment.customer_id and stripe_customer_id:
            return user_payment
        # If not, sync them
        elif stripe_customer_id:
            user_payment.customer_id = stripe_customer_id
            db.session.commit()
            return user_payment

    # If customer isn't in DB, create a new one
    user_payment = UserPayment(
        user=authenticated_user,
        customer_id=stripe_customer.get("id"),
    )
    db.session.add(user_payment)
    db.session.commit()

    return user_payment


def create_checkout(
    customer_id: str,
    lookup_key: str = Tier.PREMIUM_MONTHLY.value,
    trial_period_days: int = 0,
    success_url: str = "",
    cancel_url: str = "",
) -> stripe.checkout.Session:
    trial_period = 14
    success_url = request.host_url + "/search"
    cancel_url = request.host_url + "payment/cancel" if not cancel_url else cancel_url
    prices = stripe.Price.list(lookup_keys=[lookup_key], expand=["data.product"])

    checkout_data = {
        "customer": customer_id,
        "line_items": [
            {
                "price": prices.data[0].id,
                "quantity": 1,
            },
        ],
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "allow_promotion_codes": True
    }
    if trial_period_days:
        checkout_data["subscription_data"] = {"trial_period_days": trial_period}

    checkout_session = stripe.checkout.Session.create(**checkout_data)

    return checkout_session


def has_subscriptions(customer_id: str) -> bool:
    active_subscriptions = stripe.Subscription.list(status="active", customer=customer_id)
    trialing_subscriptions = stripe.Subscription.list(status="trialing", customer=customer_id)

    return active_subscriptions or trialing_subscriptions  # type: ignore


@payment.post("/create-checkout-session")
@login_required
@check_user_info_complete
def create_checkout_session():
    """
    DOCS: https://stripe.com/docs/payments/checkout/accept-a-payment
    """
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    try:
        user_payment = handle_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment:
        status = Status(StatusType.ERROR, PAYMENT_NOT_FOUND).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    # NOTE: Removed for now as Stripe can handle it
    # if has_subscriptions(user_payment.customer_id):
    #     status = Status(StatusType.ERROR, SUBSCRIPTION_EXISTS).get_status()
    #     return redirect(url_for("payment.index", _external=False, **status))

    tier = request.form.get("tier", "premium_monthly")
    print(tier)
    if tier not in ["premium_monthly", "premium_yearly"]:
        status = Status(StatusType.ERROR, "Invalid tier").get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    try:
        if not user_payment.customer_id:
            raise Exception(PAYMENT_NOT_FOUND)
        checkout_session = create_checkout(customer_id=user_payment.customer_id, lookup_key=tier)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    return redirect(checkout_session.url, code=303)  # type: ignore


@payment.post("/create-portal-session")
@login_required
@check_user_info_complete
def customer_portal():
    """
    DOCS: https://stripe.com/docs/customer-management/integrate-customer-portal
    """
    if request.form.get("return_url"):
        return_url = request.host_url + str(request.form.get("return_url"))
    else:
        return_url = request.host_url

    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    try:
        user_payment = handle_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment or not user_payment.customer_id:
        status = Status(StatusType.ERROR, PAYMENT_NOT_FOUND).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    portal_session = stripe.billing_portal.Session.create(
        customer=user_payment.customer_id,
        return_url=return_url,
    )

    return redirect(portal_session.url, code=303)


@payment.post("/create-portal-session-subscription-update")
@login_required
@check_user_info_complete
def subscription_update():
    """
    DOCS: https://stripe.com/docs/customer-management/integrate-customer-portal
    """
    return_url = request.host_url + "settings/plan"
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    try:
        user_payment = handle_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment or not user_payment.customer_id:
        status = Status(StatusType.ERROR, PAYMENT_NOT_FOUND).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    subscription_id = authenticated_user.user_payment.subscription_id  # type: ignore
    if not subscription_id:
        status = Status(StatusType.ERROR, "No active subscription found").get_status()
        return redirect(url_for("settings.plan", _external=False, **status))

    portal_session = stripe.billing_portal.Session.create(
        customer=user_payment.customer_id,
        return_url=return_url,
        flow_data={
            "type": "subscription_update",
            "subscription_update": {"subscription": subscription_id},
        },
    )

    return redirect(portal_session.url, code=303)


@payment.get("/create-portal-session-subscription-cancel")
@login_required
@check_user_info_complete
def subscription_cancel():
    """
    DOCS: https://stripe.com/docs/customer-management/integrate-customer-portal
    """
    return_url = request.host_url + "settings/plan"
    if current_user.is_anonymous:
        return redirect(url_for("auth.login"))

    authenticated_user: User = current_user._get_current_object()  # type: ignore

    try:
        user_payment = handle_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment or not user_payment.customer_id:
        status = Status(StatusType.ERROR, PAYMENT_NOT_FOUND).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    subscription_id = authenticated_user.user_payment.subscription_id  # type: ignore
    if not subscription_id:
        status = Status(StatusType.ERROR, "No active subscription found").get_status()
        return redirect(url_for("settings.plan", _external=False, **status))

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=user_payment.customer_id,
            return_url=return_url,
            flow_data={
                "type": "subscription_cancel",
                "subscription_cancel": {"subscription": subscription_id},
                "after_completion": {
                    "type": "redirect",
                    "redirect": {"return_url": return_url},
                },
            },
        )
    except InvalidRequestError:
        status = Status(StatusType.ERROR, "The subscription is already pending cancelation").get_status()
        return redirect(url_for("settings.plan", _external=False, **status))
    except Exception:
        status = Status(StatusType.ERROR, "Could not cancel subscription").get_status()
        return redirect(url_for("settings.plan", _external=False, **status))

    return redirect(portal_session.url, code=303)


@payment.route("/pricing", methods=["GET"])
def index():
    authenticated_user: User = current_user._get_current_object()  # type: ignore
    return render_template("payment/index.html", user=authenticated_user)


@payment.route("/success", methods=["GET"])
@login_required
@check_user_info_complete
def success():
    return render_template("payment/success.html")


@payment.route("/cancel", methods=["GET"])
@login_required
@check_user_info_complete
def cancel():
    return render_template("payment/cancel.html")


def invoice_paid(data_object):
    if data_object.get("billing_reason") != "subscription_create":
        return

    stripe_data = data_object.get("lines").get("data")[0]

    stripe_subscription_id = stripe_data.get("subscription")
    stripe_period_start = stripe_data.get("period").get("start")
    stripe_period_end = stripe_data.get("period").get("end")
    stripe_tier_price = stripe_data.get("price").get("lookup_key")
    stripe_customer_id = data_object.get("customer")
    user_payment = UserPayment.get_by_customer_id(stripe_customer_id)
    if not user_payment:
        return jsonify(success=False, error_message="Could not retrieve user payment")

    user_payment.subscription_id = stripe_subscription_id
    user_payment.expires_at_epoch = stripe_period_end
    user_payment.created_epoch = stripe_period_start
    user_payment.is_active = True

    if stripe_tier_price == "premium_monthly":
        user_payment.tier = Tier.PREMIUM_MONTHLY
    elif stripe_tier_price == "premium_yearly":
        user_payment.tier = Tier.PREMIUM_YEARLY
    try:
        Notification.mark_notifications_as_read(user_payment.user.id, NotificationDestination.SEARCH)
    except Exception as e:
        current_app.logger.warning(f"Could not mark notifications as read: {e}")
    db.session.commit()


def subscription_deleted(data_object):
    stripe_customer_id = data_object.get("customer")

    user_payment = UserPayment.get_by_customer_id(stripe_customer_id)
    if not user_payment:
        return jsonify(success=False, error_message="Could not retrieve user payment")

    user_payment.is_active = False
    user_payment.subscription_id = ""
    user_payment.created = None
    user_payment.expires_at = None
    user_payment.tier = Tier.FREE

    db.session.commit()


def subscription_updated(data):
    if data.get("object").get("cancel_at"):
        return jsonify(success=True, message="Subscription was canceled")

    stripe_customer_id = data.get("object").get("customer")
    stripe_previous_subscription = data.get("previous_attributes").get("items").get("data")[0].get("subscription")

    user_payment = UserPayment.get_by_subscription_id(stripe_previous_subscription)
    if not user_payment or user_payment.customer_id != stripe_customer_id:
        return jsonify(success=False, error_message="Could not retrieve user payment")

    lookup_key = data.get("object").get("items").get("data")[0].get("price").get("lookup_key")

    user_payment.expires_at_epoch = data.get("object").get("current_period_end")
    user_payment.tier = Tier.PREMIUM_MONTHLY if lookup_key == "premium_monthly" else Tier.PREMIUM_YEARLY
    user_payment.is_active = True
    db.session.commit()


def invoice_upcoming(data_object):
    stripe_customer_id = data_object.get("customer")
    customer_email = UserPayment.get_by_customer_id(stripe_customer_id).user.email  # type: ignore

    google_pubsub.send_event(
        "A user's subscription will be renewed",
        event_type=Events.STRIPE_INVOICE_UPCOMING.value,
        email=customer_email,
    )


def trial_will_end(data_object):
    stripe_customer_id = data_object.get("customer")
    customer_email = UserPayment.get_by_customer_id(stripe_customer_id).user.email  # type: ignore

    google_pubsub.send_event(
        "A user's trial will end soon",
        event_type=Events.STRIPE_TRIAL_WILL_END.value,
        email=customer_email,
    )


def payment_failed(data_object):
    stripe_customer_id = data_object.get("customer")
    customer_email = UserPayment.get_by_customer_id(stripe_customer_id).user.email  # type: ignore

    attempt_count = data_object.get("attempt_count")

    google_pubsub.send_event(
        "A user's subscription could not be renewed",
        event_type=Events.STRIPE_PAYMENT_FAILED.value,
        email=customer_email,
        attempt_count=attempt_count,
    )


# def new_waitlist(data_object):
#     metadata = data_object.get("metadata")
#     if product := metadata.get("product", ""):
#         if product != "teaser":
#             return jsonify(success=False, message="Invalid product")

#     stripe_customer_id = data_object.get("customer")
#     charge_id = data_object.get("id")
#     customer_email = data_object.get("customer_details").get("email")
#     if not customer_email:
#         return jsonify(success=False, message="No email found")
#     customer_name = data_object.get("customer_details").get("name", "Dear Supporter")

#     new_waitlist_charge = WaitlistCharge(
#         stripe_customer_id=stripe_customer_id,
#         charge_id=charge_id,
#         customer_email=customer_email,
#         customer_name=customer_name,
#     )
#     db.session.add(new_waitlist_charge)
#     db.session.commit()

#     user = User.get_by_email(customer_email)

#     if not user:
#         return jsonify(success=False, message="No user found")

#     notification = Notification(
#         user=user,
#         json_data=NotificationLayout(
#             title="Payment successful!",
#             msg="Thank you for supporting us!",
#         ).get_json(),
#         destination=NotificationDestination.SEARCH,
#     )
#     db.session.add(notification)
#     db.session.commit()

#     google_pubsub.send_event(
#         "A user has signed up for early access",
#         event_type=Events.STRIPE_PAYMENT_SUCCEDED.value,
#         email=customer_email,
#         random_key=new_waitlist_charge.random_key,
#     )


@payment.post("/webhook")
@csrf.exempt
def webhook_received():
    """
    DOCS: https://stripe.com/docs/webhooks
    """
    webhook_secret = os.getenv("_STRIPE_WEBHOOK_SECRET")
    request_data = json.loads(request.data)
    event = None

    if webhook_secret:
        signature = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(  # type: ignore
                payload=request.data, sig_header=signature, secret=webhook_secret
            )
            data = event["data"]
        except SignatureVerificationError as e:
            current_app.logger.warning("⚠️  Webhook signature verification failed." + str(e))
            return jsonify(success=False, error_message=e)

        event_type = event["type"]
    else:
        data = request_data["data"]
        event_type = request_data["type"]
    data_object = data["object"]

    if not event:
        return jsonify(success=False, error_message="Event not found")

    """
    DOCS: https://stripe.com/docs/billing/subscriptions/webhooks
    """

    match event_type:
        case "invoice.paid":
            invoice_paid(data_object)
        case "customer.subscription.deleted":
            subscription_deleted(data_object)
        case "customer.subscription.updated":
            subscription_updated(data)
        case "invoice.upcoming":
            invoice_upcoming(data_object)
        case "customer.subscription.trial_will_end":
            trial_will_end(data_object)
        case "invoice.payment_failed":
            payment_failed(data_object)
        # case "checkout.session.completed":
        #     """
        #     https://stripe.com/docs/payments/checkout/fulfill-orders
        #     """
        #     new_waitlist(data_object)

    return jsonify(success=True)
