from datetime import datetime

import requests
from flask_login import current_user


def track_event(event_name, properties, distinct_id):
    posthog_api_key = "phc_OYnEo3PANvSj9HM4MFbRiG5IQVyhxw3iSZXxHUOI13F"
    posthog_url = "https://app.posthog.com/capture"

    data = {
        "api_key": posthog_api_key,
        "event": event_name,
        "properties": properties,
        "distinct_id": distinct_id,
    }

    headers = {
        "Content-Type": "application/json",
        "Referer": "http://127.0.0.1:5000/",
    }

    response = requests.post(posthog_url, json=data, headers=headers)
    if response.status_code != 200:
        print(f"Failed to track event: {response.text}")


def track_page_visit(page_name: str):
    if current_user.is_authenticated:
        track_event(
            event_name="page_visited",
            properties={
                "user_id": current_user.id,
                "page": page_name,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id=current_user.id,
        )
    else:
        track_event(
            event_name="page_visited",
            properties={
                "user_id": "anonymous",
                "page": page_name,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id="anonymous",
        )


def track_subscription_attempt(subscription_type):
    if current_user.is_authenticated:
        track_event(
            event_name="subscription_purchase_attempt",
            properties={
                "user_id": current_user.id,
                "subscription_type": subscription_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id=current_user.id,
        )
    else:
        track_event(
            event_name="subscription_purchase_attempt",
            properties={
                "user_id": "anonymous",
                "subscription_type": subscription_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id="anonymous",
        )


def track_subscription_success(subscription_type, amount=0):
    if current_user.is_authenticated:
        track_event(
            event_name="subscription_purchase_success",
            properties={
                "user_id": current_user.id,
                "subscription_type": subscription_type,
                "amount": amount,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id=current_user.id,
        )
    else:
        track_event(
            event_name="subscription_purchase_success",
            properties={
                "user_id": "anonymous",
                "subscription_type": subscription_type,
                "amount": amount,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id="anonymous",
        )


def track_subscription_cancellation(subscription_type):
    if current_user.is_authenticated:
        track_event(
            event_name="subscription_cancellation",
            properties={
                "user_id": current_user.id,
                "subscription_type": subscription_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id=current_user.id,
        )
    else:
        track_event(
            event_name="subscription_cancellation",
            properties={
                "user_id": "anonymous",
                "subscription_type": subscription_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id="anonymous",
        )
