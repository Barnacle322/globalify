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
from ..utils.google_helpers.google_pubsub import send_event
from .main import check_user_info_complete

payment = Blueprint("payment", __name__)

stripe.api_key = os.getenv("_STRIPE_SECRET_KEY")


def get_invoices(authenticated_user: User):
    """
    Retrieves the invoices associated with an authenticated user.

    Args:
        authenticated_user (User): The authenticated user object.

    Returns:
        list: A list of dictionaries representing the invoices.

    Raises:
        Exception: If the user's onboarding is incomplete.

    """
    user_info = UserInfo.get_by_user_id(authenticated_user.id)
    if not user_info or not user_info.is_complete:
        raise Exception(ONBOARDING_INCOMPLETE)

    user_payment = UserPayment.get_by_user_id(authenticated_user.id)
    if not user_payment or not user_payment.customer_id:
        waitlist_charge = WaitlistCharge.get_by_customer_email(authenticated_user.email)
        if not waitlist_charge:
            return []
        stripe_invoices = stripe.PaymentIntent.list(customer=waitlist_charge.stripe_customer_id)
        print(stripe_invoices)
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
            print(invoices)
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
    """
    Handle the customer by creating or updating their payment information.

    Args:
        authenticated_user (User): The authenticated user.

    Returns:
        UserPayment: The user's payment information.

    Raises:
        Exception: If the user's onboarding is incomplete.
        Exception: If the email is already associated with multiple customers.

    """
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
    customer_id: str, tier: str = "elevate", trial_period_days: int = 0, success_url: str = "", cancel_url: str = ""
) -> stripe.checkout.Session:
    """
    Create a Stripe checkout session for a customer subscription.

    This function initializes a Stripe checkout session with different
    configurations based on the specified tier and trial period. It can also
    handle custom success and cancellation URLs.

    Args:
        customer_id (str): The Stripe Customer ID to create a session for.
        tier (str, optional): The subscription tier. Defaults to 'elevate'.
        trial_period_days (int, optional): The trial period in days. Defaults to 0.
        success_url (str, optional): URL to redirect to on successful payment.
        cancel_url (str, optional): URL to redirect to on checkout cancellation.

    Returns:
        stripe.checkout.Session: The Stripe Checkout Session object.

    Note:
        The tier can be one of the following with their respective meanings:
        - 'elevate': Elevate tier
        - 'connect': Connect Pro tier
        - 'boost': Boost Academy tier
        - 'teaser': Waitlist tier
        The 'elevate' tier has a default trial period of 14 days.
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
            allow_promotion_codes=True,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"product": "teaser"},  # type: ignore
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


def waitlist(email: str, first_name: str, last_name: str, user: User):
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
        checkout_session = create_checkout(
            customer_id=stripe_customer.get("id", ""),
            tier="teaser",
            cancel_url=request.host_url + "waitlist/cancel",
            success_url=request.host_url + "search",
        )
    except Exception as e:
        status = Status(StatusType.ERROR, e.args[0]).get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    Notification.mark_notifications_as_read(
        user_id=user.id,
        destination=NotificationDestination.SEARCH,
    )

    notification = Notification(
        user=user,
        json_data=NotificationLayout(
            title="Onboarding completed!!",
            msg="Go and try our suggestions!",
            buttons=[ButtonLayout(text="Try!", url=url_for("main.get_suggestions"))],
        ).get_json(),
        destination=NotificationDestination.SEARCH,
    )
    db.session.add(notification)
    db.session.commit()

    return redirect(checkout_session.url, code=303)  # type: ignore


@payment.post("/create-checkout-session")
@login_required
@check_user_info_complete
def create_checkout_session():
    """
    DOCS: https://stripe.com/docs/payments/checkout/accept-a-payment

    Creates a new checkout session for a logged-in and verified user.

    Returns:
        A redirect to the Stripe checkout session URL on success, or a
        redirect to the payment index page with an error status on failure.

    Raises:
        Exception: If any error occurs while handling the customer or creating
        the checkout session.

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

    tier = request.form.get("tier", "elevate")
    if tier not in ["elevate", "connect", "boost"]:
        status = Status(StatusType.ERROR, "Invalid tier").get_status()
        return redirect(url_for("payment.index", _external=False, **status))

    try:
        if not user_payment.customer_id:
            raise Exception(PAYMENT_NOT_FOUND)
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

    Redirects an authenticated and verified user to the Stripe Customer Portal.

    Returns:
        A redirect to the Stripe Customer Portal session URL on success, or a
        redirect to the payment index page with an error status on failure.

    Raises:
        Exception: If any error occurs while handling the customer or creating
        the portal session.
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

    Creates a session for an authenticated user to update their subscription.

    Returns:
        A redirect to the Stripe Customer Portal with subscription update flow,
        or a redirect to the payment index page with an error status on failure.

    Raises:
        Exception: If an error occurs while handling the customer or creating the
        portal session.
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

    Creates a session for an authenticated user to cancel their subscription.

    Returns:
        A redirect to the Stripe Customer Portal with subscription cancel flow,
        or a redirect to the settings plan page with an error status on failure.

    Raises:
        InvalidRequestError: If the subscription is already pending cancellation.
        Exception: If an error occurs while handling the customer or creating the
        portal session.

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
    """
    Updates the user's payment information and subscription details based on the given Stripe data.

    Parameters:
    - data_object: A dictionary containing the Stripe data.

    Returns:
    - None if the charge is not for a subscription.
    - JSON response with success status and error message if user payment retrieval fails.

    """
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

    send_event(
        "A user's subscription will be renewed",
        event_type=Events.STRIPE_INVOICE_UPCOMING.value,
        email=customer_email,
    )


def trial_will_end(data_object):
    stripe_customer_id = data_object.get("customer")
    customer_email = UserPayment.get_by_customer_id(stripe_customer_id).user.email  # type: ignore

    send_event(
        "A user's trial will end soon",
        event_type=Events.STRIPE_TRIAL_WILL_END.value,
        email=customer_email,
    )


def payment_failed(data_object):
    stripe_customer_id = data_object.get("customer")
    customer_email = UserPayment.get_by_customer_id(stripe_customer_id).user.email  # type: ignore

    attempt_count = data_object.get("attempt_count")

    send_event(
        "A user's subscription could not be renewed",
        event_type=Events.STRIPE_PAYMENT_FAILED.value,
        email=customer_email,
        attempt_count=attempt_count,
    )


def new_waitlist(data_object):
    metadata = data_object.get("metadata")
    if product := metadata.get("product", ""):
        if product != "teaser":
            return jsonify(success=False, message="Invalid product")

    stripe_customer_id = data_object.get("customer")
    charge_id = data_object.get("id")
    customer_email = data_object.get("customer_details").get("email")
    if not customer_email:
        return jsonify(success=False, message="No email found")
    customer_name = data_object.get("customer_details").get("name", "Dear Supporter")

    new_waitlist_charge = WaitlistCharge(
        stripe_customer_id=stripe_customer_id,
        charge_id=charge_id,
        customer_email=customer_email,
        customer_name=customer_name,
    )
    db.session.add(new_waitlist_charge)
    db.session.commit()

    user = User.get_by_email(customer_email)

    if not user:
        return jsonify(success=False, message="No user found")

    notification = Notification(
        user=user,
        json_data=NotificationLayout(
            title="Payment successful!",
            msg="Thank you for supporting us!",
        ).get_json(),
        destination=NotificationDestination.SEARCH,
    )
    db.session.add(notification)
    db.session.commit()

    send_event(
        "A user has signed up for early access",
        event_type=Events.STRIPE_PAYMENT_SUCCEDED.value,
        email=customer_email,
        random_key=new_waitlist_charge.random_key,
    )


@payment.post("/webhook")
@csrf.exempt
def webhook_received():
    """
    DOCS: https://stripe.com/docs/webhooks

    Receives and processes webhook events from Stripe.

    This endpoint is called by Stripe when various events occur,
    such as payment successes or failures. It verifies the webhook
    signature, parses the event, and then delegates to the appropriate
    handler function based on the event type.

    Returns:
        Response: A JSON response indicating the success or failure of processing the webhook.

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
        case "invoice.upcoming":
            invoice_upcoming(data_object)
        case "customer.subscription.trial_will_end":
            trial_will_end(data_object)
        case "invoice.payment_failed":
            payment_failed(data_object)
        case "checkout.session.completed":
            """
            https://stripe.com/docs/payments/checkout/fulfill-orders
            """
            new_waitlist(data_object)

    return jsonify(success=True)
