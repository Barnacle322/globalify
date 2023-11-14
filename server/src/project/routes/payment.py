import json
import os
from datetime import datetime

import stripe
from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from stripe.error import InvalidRequestError, SignatureVerificationError

from ..extensions import csrf, db
from ..models import User, UserInfo, UserPayment, WaitlistCharge
from ..utils.errors.auth_error_messages import (
    ONBOARDING_INCOMPLETE,
    PAYMENT_EMAIL_USED,
    PAYMENT_NOT_FOUND,
)
from ..utils.sendgrid_email import send_email
from ..utils.status_enum import Status, StatusType, Tier
from .main import check_user_info_complete

payment = Blueprint("payment", __name__)

stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")


def get_invoices(authenticated_user: User):
    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info or not user_info.is_complete:
        raise Exception(ONBOARDING_INCOMPLETE)

    user_payment = UserPayment.get_by_user_id(authenticated_user.id)
    if not user_payment or not user_payment.customer_id:
        return []

    stripe_invoices = stripe.Invoice.list(customer=user_payment.customer_id)
    invoices = []
    for stripe_invoice in stripe_invoices:
        invoice = {
            "id": stripe_invoice.get("id"),
            "created": datetime.utcfromtimestamp(stripe_invoice.get("created", 0)).date(),
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
        user_id=authenticated_user.id,
        customer_id=stripe_customer.get("id"),
    )
    db.session.add(user_payment)
    db.session.commit()

    return user_payment


def create_checkout(
    customer_id: str, tier: str = "elevate", trial_period_days: int = 0, success_url: str = "", cancel_url: str = ""
) -> stripe.checkout.Session:
    """
    Elevate: elevate
    Connect Pro: connect
    Boost Academy: boost
    Waitlist: teaser
    """
    elevate_trial_period_days = 14
    success_url = (
        request.host_url + "payment/success?session_id={CHECKOUT_SESSION_ID}" if not success_url else success_url
    )
    cancel_url = request.host_url + "payment/cancel" if not cancel_url else cancel_url
    prices = stripe.Price.list(lookup_keys=[tier], expand=["data.product"])

    if tier == "teaser":
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[
                {
                    "price": prices.data[0].id,
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=success_url,
            cancel_url=cancel_url,
        )
    elif tier == "elevate":
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[
                {
                    "price": prices.data[0].id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            subscription_data={"trial_period_days": elevate_trial_period_days},
        )
    elif trial_period_days != 0:
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[
                {
                    "price": prices.data[0].id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            subscription_data={"trial_period_days": trial_period_days},
        )
    else:
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            line_items=[
                {
                    "price": prices.data[0].id,
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )

    return checkout_session


def has_subscriptions(customer_id: str) -> bool:
    active_subscriptions = stripe.Subscription.list(status="active", customer=customer_id)
    trialing_subscriptions = stripe.Subscription.list(status="trialing", customer=customer_id)

    return active_subscriptions or trialing_subscriptions  # type: ignore


@payment.post("/waitlist")
def waitlist():
    email = request.form.get("email", "")
    first_name = request.form.get("first-name", "")
    last_name = request.form.get("last-name", "")

    full_name = f"{first_name} {last_name}"

    customer_data = stripe.Customer.search(query=f"email:'{email}'")

    if len(customer_list := customer_data.get("data", [])) > 1:
        raise Exception(PAYMENT_EMAIL_USED)
    elif not customer_list:
        stripe_customer = stripe.Customer.create(
            email=email,
            name=full_name,
        )
    else:
        stripe_customer = customer_list[0]

    try:
        checkout_session = create_checkout(customer_id=stripe_customer.get("id", ""), tier="teaser")
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    return redirect(checkout_session.url, code=303)  # type: ignore


@payment.post("/create-checkout-session")
@login_required
@check_user_info_complete
def create_checkout_session():
    """
    DOCS: https://stripe.com/docs/payments/checkout/accept-a-payment
    """
    authenticated_user: User = current_user  # type: ignore
    if authenticated_user.is_anonymous:
        return redirect(url_for("auth.login"))

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

    tier = request.form.get("tier", "elevate")
    if tier not in ["elevate", "connect", "boost"]:
        status = Status(StatusType.ERROR, "Invalid tier").get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    try:
        checkout_session = create_checkout(customer_id=user_payment.customer_id, tier=tier)
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

    authenticated_user: User = current_user  # type: ignore
    if authenticated_user.is_anonymous:
        return redirect(url_for("auth.login"))

    try:
        user_payment = handle_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment:
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
    authenticated_user: User = current_user  # type: ignore
    if authenticated_user.is_anonymous:
        return redirect(url_for("auth.login"))

    try:
        user_payment = handle_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment:
        status = Status(StatusType.ERROR, PAYMENT_NOT_FOUND).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    subscription_id = request.form.get("subscription_id", "")

    portal_session = stripe.billing_portal.Session.create(
        customer=user_payment.customer_id,
        return_url=return_url,
        flow_data={
            "type": "subscription_update",
            "subscription_update": {"subscription": subscription_id},
        },
    )

    return redirect(portal_session.url, code=303)


@payment.post("/create-portal-session-subscription-cancel")
@login_required
@check_user_info_complete
def subscription_cancel():
    """
    DOCS: https://stripe.com/docs/customer-management/integrate-customer-portal
    """
    return_url = request.host_url + "settings/plan"
    authenticated_user: User = current_user  # type: ignore
    if authenticated_user.is_anonymous:
        return redirect(url_for("auth.login"))

    try:
        user_payment = handle_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment:
        status = Status(StatusType.ERROR, PAYMENT_NOT_FOUND).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    subscription_id = request.form.get("subscription_id", "")

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
    return render_template("payment/index.html")


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
    # Check for the charge to be a subscription
    if data_object.get("billing_reason") != "subscription_create":
        return

    stripe_data = data_object.get("lines").get("data")[0]

    stripe_subscription_id = stripe_data.get("subscription")
    stripe_period_start = stripe_data.get("period").get("start")
    stripe_period_end = stripe_data.get("period").get("end")
    stripe_tier = stripe_data.get("price").get("lookup_key")
    stripe_customer_id = data_object.get("customer")
    user_payment = UserPayment.get_by_customer_id(stripe_customer_id)
    if not user_payment:
        return jsonify(success=False, error_message="Could not retrieve user payment")

    user_payment.subscription_id = stripe_subscription_id
    user_payment.expires_at_epoch = stripe_period_end
    user_payment.created_epoch = stripe_period_start
    user_payment.is_active = True

    if stripe_tier == "elevate":
        user_payment.tier = Tier.ELEVATE
    elif stripe_tier == "connect":
        user_payment.tier = Tier.CONNECT
    elif stripe_tier == "boost":
        user_payment.tier = Tier.BOOST

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


def invoice_upcoming(data_object):
    stripe_customer_id = data_object.get("customer")
    customer_email = UserPayment.get_by_customer_id(stripe_customer_id).user.email  # type: ignore

    html_content = render_template("email/invoice_upcoming.html")

    send_email(
        recepients=customer_email,
        subject="Your subscription will be soon renewed",
        html_content=html_content,
    )


def trial_will_end(data_object):
    stripe_customer_id = data_object.get("customer")
    customer_email = UserPayment.get_by_customer_id(stripe_customer_id).user.email  # type: ignore

    html_content = render_template("email/subscription_expires.html")

    send_email(
        recepients=customer_email,
        subject="Your trial ends soon!",
        html_content=html_content,
    )


def payment_failed(data_object):
    stripe_customer_id = data_object.get("customer")
    customer_email = UserPayment.get_by_customer_id(stripe_customer_id).user.email  # type: ignore

    attempt_count = data_object.get("attempt_count")
    html_content = render_template("email/payment_failed.html", attempt_count=attempt_count)

    send_email(
        recepients=customer_email,
        subject="Subscription could not be renewed",
        html_content=html_content,
    )


def charge_succeeded(data_object):
    if int(data_object.get("amount")) != 5000:
        return jsonify(success=True)

    stripe_customer_id = data_object.get("customer")
    charge_id = data_object.get("id")
    customer_email = data_object.get("billing_details").get("email")
    customer_name = data_object.get("billing_details").get("name")

    new_waitlist_charge = WaitlistCharge(
        stripe_customer_id=stripe_customer_id,
        charge_id=charge_id,
        customer_email=customer_email,
        customer_name=customer_name,
    )
    db.session.add(new_waitlist_charge)
    db.session.commit()

    html_content = render_template("email/payment_succeeded.html", uuid=new_waitlist_charge.random_key)

    send_email(
        recepients=customer_email,
        subject="Your have signed up for the waitlist!",
        html_content=html_content,
    )


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
    # TODO: Add an event to handle the teaser product
    # charge.succeded checkout.session.completed payment_intent.created payment_intent.succeeded
    match event_type:
        case "invoice.paid":
            invoice_paid(data_object)
        case "customer.subscription.deleted":
            subscription_deleted(data_object)
        case "invoice.upcoming":
            invoice_upcoming(data_object)
        case "customer.subscription.trial_will_end":
            trial_will_end(data_object)
        case "invoice.payment_failed":
            payment_failed(data_object)
        case "charge.succeeded":
            charge_succeeded(data_object)

    return jsonify(success=True)
