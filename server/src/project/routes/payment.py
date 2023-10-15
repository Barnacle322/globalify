import json
import os
from datetime import datetime

import stripe
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import AnonymousUserMixin, current_user, login_required
from stripe.error import InvalidRequestError, SignatureVerificationError

from ..extensions import csrf, db
from ..models import User, UserInfo, UserPayment
from ..utils.errors.auth_error_messages import (
    ONBOARDING_INCOMPLETE,
    PAYMENT_EMAIL_USED,
    PAYMENT_NOT_FOUND,
    SUBSCRIPTION_EXISTS,
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
    if not user_payment:
        return []

    stripe_invoices = stripe.Invoice.list(customer=user_payment.customer_id)
    invoices = []
    for stripe_invoice in stripe_invoices:
        invoice = {
            "id": stripe_invoice.get("id"),
            "created": datetime.utcfromtimestamp(stripe_invoice.get("created")).date(),
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
    customer_data = stripe.Customer.search(
        query="email:'{}'".format(authenticated_user.email)
    )
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
        if (
            user_payment.customer_id == stripe_customer_id
            and user_payment.customer_id
            and stripe_customer_id
        ):
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
    customer_id: str,
    trial_period_days: int = 14,
    tier: str = "elevate",
) -> stripe.checkout.Session:
    """
    Elevate: elevate
    Connect Pro: connect
    Boost Academy: boost
    """
    success_url = request.host_url + "payment/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.host_url + "payment/cancel"
    prices = stripe.Price.list(lookup_keys=[tier], expand=["data.product"])

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

    return checkout_session


def has_subscriptions(customer_id: str) -> bool:
    active_subscriptions = stripe.Subscription.list(
        status="active", customer=customer_id
    )
    trialing_subscriptions = stripe.Subscription.list(
        status="trialing", customer=customer_id
    )

    return active_subscriptions or trialing_subscriptions  # type: ignore


@payment.route("/create-checkout-session", methods=["POST"])
@login_required
@check_user_info_complete
def create_checkout_session():
    """
    DOCS: https://stripe.com/docs/payments/checkout/accept-a-payment
    """
    authenticated_user: User = current_user  # type: ignore
    if isinstance(authenticated_user, AnonymousUserMixin):
        return redirect(url_for("auth.login"))

    try:
        user_payment = handle_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment:
        status = Status(StatusType.ERROR, PAYMENT_NOT_FOUND).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if has_subscriptions(user_payment.customer_id):
        status = Status(StatusType.ERROR, SUBSCRIPTION_EXISTS).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    try:
        checkout_session = create_checkout(customer_id=user_payment.customer_id)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))  # type: ignore

    return redirect(checkout_session.url, code=303)


@payment.route("/create-portal-session", methods=["POST"])
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
    if isinstance(authenticated_user, AnonymousUserMixin):
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


@payment.route("/create-portal-session-subscription-update", methods=["POST"])
@login_required
@check_user_info_complete
def subscription_update():
    """
    DOCS: https://stripe.com/docs/customer-management/integrate-customer-portal
    """
    return_url = request.host_url + "settings/plan"
    authenticated_user: User = current_user  # type: ignore
    if isinstance(authenticated_user, AnonymousUserMixin):
        return redirect(url_for("auth.login"))

    try:
        user_payment = handle_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment:
        status = Status(StatusType.ERROR, PAYMENT_NOT_FOUND).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    subscription_id = request.form.get("subscription_id")

    portal_session = stripe.billing_portal.Session.create(
        customer=user_payment.customer_id,
        return_url=return_url,
        flow_data={
            "type": "subscription_update",
            "subscription_update": {"subscription": subscription_id},
        },
    )

    return redirect(portal_session.url, code=303)


@payment.route("/create-portal-session-subscription-cancel", methods=["POST"])
@login_required
@check_user_info_complete
def subscription_cancel():
    """
    DOCS: https://stripe.com/docs/customer-management/integrate-customer-portal
    """
    return_url = request.host_url + "settings/plan"
    authenticated_user: User = current_user  # type: ignore
    if isinstance(authenticated_user, AnonymousUserMixin):
        return redirect(url_for("auth.login"))

    try:
        user_payment = handle_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment:
        status = Status(StatusType.ERROR, PAYMENT_NOT_FOUND).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    subscription_id = request.form.get("subscription_id")

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
        status = Status(
            StatusType.ERROR, "The subscription is already pending cancelation"
        ).get_status()
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
    html_content = render_template(
        "email/payment_failed.html", attempt_count=attempt_count
    )

    send_email(
        recepients=customer_email,
        subject="Subscription could not be renewed",
        html_content=html_content,
    )


@payment.route("/webhook", methods=["POST"])
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
            event = stripe.Webhook.construct_event(
                payload=request.data, sig_header=signature, secret=webhook_secret  # type: ignore
            )
            data = event["data"]
        except SignatureVerificationError as e:
            print("⚠️  Webhook signature verification failed." + str(e))
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
        case "invoice.upcoming":
            invoice_upcoming(data_object)
        case "customer.subscription.trial_will_end":
            trial_will_end(data_object)
        case "invoice.payment_failed":
            payment_failed(data_object)

    return jsonify(success=True)
