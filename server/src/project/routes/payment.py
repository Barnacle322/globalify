import json
import os
from typing import Union

import stripe
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import User, UserPayment
from ..utils import Status, StatusType

payment = Blueprint("payment", __name__)

stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")


def create_customer(authenticated_user: User) -> Union[UserPayment, None]:
    user_payment = None
    try:
        if not (user_payment := UserPayment.get_by_user_id(authenticated_user.id)):
            customer = stripe.Customer.create(
                email=authenticated_user.email,
            )
            user_payment = UserPayment(
                user_id=authenticated_user.id,
                customer_id=customer.id,
            )
            db.session.add(user_payment)
            db.session.commit()
    except Exception:
        db.session.rollback()
    finally:
        db.session.close()

    return user_payment


def create_checkout(
    customer_id: str, trial_period_days: int = 14
) -> stripe.checkout.Session:
    success_url = request.host_url + "payment/success?session_id={CHECKOUT_SESSION_ID}"
    cancel_url = request.host_url + "payment/cancel"

    checkout_session = stripe.checkout.Session.create(
        customer=customer_id,
        line_items=[
            {
                "price": "price_1NdKLmDsBtpSnIdQdw4tyKam",
                "quantity": 1,
            },
        ],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        subscription_data={"trial_period_days": trial_period_days},
    )

    return checkout_session


@payment.route("/", methods=["GET"])
@login_required
def index():
    return render_template("payment/index.html")


@payment.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    authenticated_user: User = current_user  # type: ignore
    user_payment = create_customer(authenticated_user)

    if not user_payment:
        status = Status(StatusType.ERROR, "User payment not found").get_status()
        return redirect(url_for("payment.index", **status))  # type: ignore

    subscriptions = stripe.Subscription.list(customer=user_payment.customer_id)
    print(subscriptions)
    return subscriptions
    # checkout_session = create_checkout(customer_id=user_payment.customer_id)

    # return redirect(checkout_session.url, code=303)


@payment.route("/success", methods=["GET"])
@login_required
def success():
    return render_template("payment/success.html")


@payment.route("/create-portal-session", methods=["POST"])
@login_required
def customer_portal():
    return_url = request.host_url
    authenticated_user: User = current_user  # type: ignore
    user_payment = create_customer(authenticated_user)

    if not user_payment:
        status = Status(StatusType.ERROR, "User payment not found").get_status()
        return redirect(url_for("payment.index", **status))  # type: ignore

    portalSession = stripe.billing_portal.Session.create(
        customer=user_payment.customer_id,
        return_url=return_url,
    )
    return redirect(portalSession.url, code=303)


@payment.route("/webhook", methods=["POST"])
def webhook_received():
    # Replace this endpoint secret with your endpoint's unique secret
    # If you are testing with the CLI, find the secret by running 'stripe listen'
    # If you are using an endpoint defined with the API or dashboard, look in your webhook settings
    # at https://dashboard.stripe.com/webhooks
    webhook_secret = os.getenv("_STRIPE_WEBHOOK_SECRET")
    request_data = json.loads(request.data)

    if webhook_secret:
        # Retrieve the event by verifying the signature using the raw body and secret if webhook signing is configured.
        signature = request.headers.get("stripe-signature")
        try:
            event = stripe.Webhook.construct_event(
                payload=request.data, sig_header=signature, secret=webhook_secret  # type: ignore
            )
            data = event["data"]
        except Exception as e:
            return {"status": "error", "message": str(e)}, 403
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event["type"]
    else:
        data = request_data["data"]
        event_type = request_data["type"]
    data_object = data["object"]  # noqa

    if event_type == "checkout.session.completed":
        print("🔔 Payment succeeded!")
    elif event_type == "customer.subscription.trial_will_end":
        print("Subscription trial will end")
    elif event_type == "customer.subscription.created":
        print("Subscription created %s", event.id)  # type: ignore
    elif event_type == "customer.subscription.updated":
        is_canceled = data_object.get("canceled_at")
        if is_canceled:
            print("Subscription canceled %s", event.id)  # type: ignore
        print("-------------------")
        print(data_object)
        print("Subscription created %s", event.id)  # type: ignore
        print("-------------------")
    elif event_type == "customer.subscription.deleted":
        # handle subscription canceled automatically based
        # upon your subscription settings. Or if the user cancels it.
        print("Subscription canceled: %s", event.id)  # type: ignore

    return {"status": "success"}


# @payment.errorhandler(Exception)
# def exception_handler(e):
#     return render_template("errors/500.html")
