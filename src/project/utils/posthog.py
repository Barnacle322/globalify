import os
from datetime import datetime

import posthog
from flask_login import current_user

posthog.api_key = os.getenv("_POSTHOG_API_KEY")
posthog.host = "https://app.posthog.com"


def track_event(event_name, properties, distinct_id):
    posthog.capture(distinct_id=distinct_id, event=event_name, properties=properties)


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


def track_subscription_success(subscription_type, user=None):
    if user:
        track_event(
            event_name="subscription_purchase_success",
            properties={
                "user_id": user.id,
                "subscription_type": subscription_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id=user.email,
        )
    else:
        track_event(
            event_name="subscription_purchase_success",
            properties={
                "user_id": "anonymous",
                "subscription_type": subscription_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id="anonymous",
        )


def track_subscription_cancellation(subscription_type, user=None):
    if user:
        track_event(
            event_name="subscription_cancellation",
            properties={
                "user_id": user.id,
                "subscription_type": subscription_type,
                "timestamp": datetime.utcnow().isoformat(),
            },
            distinct_id=user.id,
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
