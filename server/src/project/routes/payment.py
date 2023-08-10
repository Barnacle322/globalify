import json
import os
import stripe

from flask import Blueprint, jsonify, redirect, render_template, request


payment = Blueprint("payment", __name__)

stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")


@payment.route("/", methods=["GET"])
def index():
    return render_template("payment/index.html")


@payment.route("/success", methods=["GET"])
def success():
    return render_template("payment/success.html")


@payment.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    print()
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    "price": "price_1NdKLmDsBtpSnIdQdw4tyKam",
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=(
                request.host_url + "/payment/success?session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=f"{request.host_url}/payment/cancel",
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        raise e


@payment.route("/create-portal-session", methods=["POST"])
def customer_portal():
    # TODO: For demonstration purposes, we're using the Checkout session to retrieve the customer ID.
    # Typically this is stored alongside the authenticated user in your database.
    if not (checkout_session_id := request.form.get("session_id")):
        return (
            jsonify({"error": {"message": "Missing stripe checkout session id"}}),
            400,
        )

    checkout_session = stripe.checkout.Session.retrieve(checkout_session_id)

    # This is the URL to which the customer will be redirected after they are
    # done managing their billing with the portal.
    return_url = request.host_url

    portalSession = stripe.billing_portal.Session.create(
        customer=checkout_session.customer,
        return_url=return_url,
    )
    return redirect(portalSession.url, code=303)


@payment.route("/webhook", methods=["POST"])  # type: ignore
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
            return e
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event["type"]
    else:
        data = request_data["data"]
        event_type = request_data["type"]
    data_object = data["object"]  # noqa

    print("event " + event_type)

    if event_type == "checkout.session.completed":
        print("🔔 Payment succeeded!")
    elif event_type == "customer.subscription.trial_will_end":
        print("Subscription trial will end")
    elif event_type == "customer.subscription.created":
        print("Subscription created %s", event.id)  # type: ignore
    elif event_type == "customer.subscription.updated":
        print("Subscription created %s", event.id)  # type: ignore
    elif event_type == "customer.subscription.deleted":
        # handle subscription canceled automatically based
        # upon your subscription settings. Or if the user cancels it.
        print("Subscription canceled: %s", event.id)  # type: ignore

    return jsonify({"status": "success"})


@payment.errorhandler(Exception)
def exception_handler(e):
    return render_template("errors/500.html")
