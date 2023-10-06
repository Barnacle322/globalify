import json
import os

import stripe
from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from stripe.error import SignatureVerificationError

from ..extensions import csrf, db
from ..models import User, UserInfo, UserPayment
from ..utils.errors.auth_error_messages import NOT_AUTHORIZED
from ..utils.status_enum import Status, StatusType

payment = Blueprint("payment", __name__)

stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")


def create_customer(authenticated_user: User) -> UserPayment:
    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info or not user_info.is_complete:
        raise Exception("Please complete your profile before subscribing")

    # Find customer by email
    customer_data = stripe.Customer.search(
        query="email:'{}'".format(authenticated_user.email)
    )
    # If multiple customers are found, raise an exception
    if len(customer_list := customer_data.get("data", [])) > 1:
        raise Exception(
            "Multiple customers associated with your email address are found. Please contact support."
        )
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
    tier: str = "basic",
) -> stripe.checkout.Session:
    success_url = request.host_url + "payment/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.host_url + "payment/cancel"

    try:
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
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))  # type: ignore

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
def create_checkout_session():
    """
    DOCS: https://stripe.com/docs/payments/checkout/accept-a-payment
    """
    authenticated_user: User = current_user  # type: ignore
    if not authenticated_user:
        status = Status(StatusType.ERROR, NOT_AUTHORIZED).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    try:
        user_payment = create_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if not user_payment:
        status = Status(StatusType.ERROR, "User payment not found").get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    if has_subscriptions(user_payment.customer_id):
        status = Status(StatusType.ERROR, "A subscription already exists").get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    checkout_session = create_checkout(customer_id=user_payment.customer_id)

    return redirect(checkout_session.url, code=303)


@payment.route("/subscriptions", methods=["GET"])
def index():
    return render_template("payment/index.html")


@payment.route("/success", methods=["GET"])
@login_required
def success():
    return render_template("payment/success.html")


@payment.route("/cancel", methods=["GET"])
@login_required
def cancel():
    return render_template("payment/cancel.html")


@payment.route("/create-portal-session", methods=["POST"])
@login_required
def customer_portal():
    """
    DOCS: https://stripe.com/docs/customer-management/integrate-customer-portal
    """

    return_url = request.host_url
    authenticated_user: User = current_user  # type: ignore
    if not authenticated_user:
        status = Status(StatusType.ERROR, NOT_AUTHORIZED).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    user_payment = create_customer(authenticated_user)
    if not user_payment:
        status = Status(StatusType.ERROR, "User payment not found").get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    portal_session = stripe.billing_portal.Session.create(
        customer=user_payment.customer_id,
        return_url=return_url,
    )

    return redirect(portal_session.url, code=303)


# TODO
@payment.route("/webhook", methods=["POST"])
@csrf.exempt
def webhook_received():  # noqa
    """
    DOCS: https://stripe.com/docs/webhooks
    """
    webhook_secret = os.getenv("_STRIPE_WEBHOOK_SECRET")
    request_data = json.loads(request.data)
    event = None

    if webhook_secret:
        # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
        signature = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(
                payload=request.data, sig_header=signature, secret=webhook_secret  # type: ignore
            )
            data = event["data"]
        except SignatureVerificationError as e:
            print("⚠️  Webhook signature verification failed." + str(e))
            return jsonify(success=False)
        event_type = event["type"]
    else:
        data = request_data["data"]
        event_type = request_data["type"]
    data_object = data["object"]  # noqa

    if not event:
        return jsonify(success=False)

    if event_type == "invoice.paid":
        stripe_customer_id = data_object.get("customer")
        user_payment = UserPayment.get_by_customer_id(stripe_customer_id)
        if not user_payment:
            return {"status": "fail"}, 200

        user_payment.created_epoch = data_object.get("effective_at")
        user_payment.expires_at_epoch = (
            data_object.get("lines").get("data")[0].get("period").get("end")
        )
        user_payment.is_active = True
        user_payment.subscription_id = (
            data_object.get("lines").get("data")[0].get("subscription")
        )

        db.session.commit()

    if event_type == "customer.subscription.deleted":
        stripe_customer_id = data_object.get("customer")
        user_payment = UserPayment.get_by_customer_id(stripe_customer_id)
        if not user_payment:
            return {"status": "fail"}, 200

        user_payment.is_active = False
        user_payment.subscription_id = ""

        db.session.commit()

    if event_type == "invoice.upcoming":
        # Add logic to send an email to user about an upcoming charge
        ...

    if event_type == "customer.subscription.trial_will_end":
        # Add logic to send an email to user about their trial ending soon
        ...

    if event_type == "invoice.payment_failed":
        # Add logic that notifies user that their payment failed
        # NOTE: use 'attempt_count' and 'attempted' to determine if this is the first time the payment failed
        # After the 4th attempt the subscription was cenceled with the 'customer.subscription.deleted' event
        ...

    # # if event_type == "checkout.session.completed":
    #     print("🔔 Payment succeeded!")
    # elif event_type == "customer.subscription.trial_will_end":
    #     print("Subscription trial will end")
    # elif event_type == "customer.subscription.created":
    #     print("Subscription created %s", event.id)
    # elif event_type == "customer.subscription.updated":
    #     is_canceled = data_object.get("canceled_at")
    #     if is_canceled:
    #         print("Subscription canceled %s", event.id)
    # elif event_type == "customer.subscription.deleted":
    #     print("Subscription canceled: %s", event.id)

    # NOTE: This endpoint should return 200 - 299 to acknowledge receipt of the event.
    return {"status": "success"}, 200
