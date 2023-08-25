import json
import os

import stripe
from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..extensions import db
from ..models import User, UserPayment
from ..utils import Status, StatusType

payment = Blueprint("payment", __name__)

stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")


def create_customer(authenticated_user: User):
    user_payment = UserPayment.get_by_user_id(authenticated_user.id)
    if not user_payment:
        customer_data = stripe.Customer.search(
            query="email:'{}'".format(authenticated_user.email),
        )

        if not customer_data:
            customer = stripe.Customer.create(
                email=authenticated_user.email,
            )

        elif len(customer_list := customer_data.get("data")) == 1:  # type: ignore
            customer = customer_list[0]  # type: ignore

        else:
            raise Exception(
                "Multiple customers with same email found. Please contact support."
            )

        user_payment = UserPayment(
            user_id=authenticated_user.id,
            customer_id=customer.id,
        )

        db.session.add(user_payment)
        db.session.commit()

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


def no_subscriptions(customer_id: str):
    active_subscriptions = stripe.Subscription.list(
        status="active", customer=customer_id
    )
    trialing_subscriptions = stripe.Subscription.list(
        status="trialing", customer=customer_id
    )

    return True if not (active_subscriptions and trialing_subscriptions) else False


@payment.route("/", methods=["GET"])
@login_required
def index():
    return render_template("payment/index.html")


@payment.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    """
    DOCS: https://stripe.com/docs/payments/checkout/accept-a-payment
    """
    authenticated_user: User = current_user  # type: ignore
    if not authenticated_user:
        status = Status(StatusType.ERROR, "You are not logged in").get_status()
        return redirect(url_for("payment.index", **status))  # type: ignore

    try:
        user_payment = create_customer(authenticated_user)
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0])
        return redirect(url_for("payment.index", **status))  # type: ignore

    if not user_payment:
        status = Status(StatusType.ERROR, "User payment not found").get_status()
        return redirect(url_for("payment.index", **status))  # type: ignore

    if no_subscriptions(user_payment.customer_id):
        status = Status(
            StatusType.ERROR, "A subscription is already exists"
        ).get_status()
        return redirect(url_for("payment.index", **status))  # type: ignore

    checkout_session = create_checkout(customer_id=user_payment.customer_id)

    return redirect(checkout_session.url, code=303)


@payment.route("/success", methods=["GET"])
@login_required
def success():
    return render_template("payment/success.html")


@payment.route("/create-portal-session", methods=["POST"])
@login_required
def customer_portal():
    """
    DOCS: https://stripe.com/docs/customer-management/integrate-customer-portal
    """

    return_url = request.host_url
    authenticated_user: User = current_user  # type: ignore
    user_payment = create_customer(authenticated_user)

    if not user_payment:
        status = Status(StatusType.ERROR, "User payment not found").get_status()
        return redirect(url_for("payment.index", **status))  # type: ignore

    portal_session = stripe.billing_portal.Session.create(
        customer=user_payment.customer_id,
        return_url=return_url,
    )
    return redirect(portal_session.url, code=303)


# TODO
@payment.route("/webhook", methods=["POST"])
def webhook_received():
    """
    DOCS: https://stripe.com/docs/webhooks
    """
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
