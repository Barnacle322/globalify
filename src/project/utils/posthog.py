import os
from datetime import UTC, datetime
from typing import Any

import posthog
from flask_login import current_user

posthog.api_key = os.getenv("_POSTHOG_API_KEY")
posthog.host = "https://us.i.posthog.com"


def capture_event(
    distinct_id: str,
    event: str,
    properties: dict[Any, Any] | None = None,
    context: dict[Any, Any] | None = None,
    timestamp: datetime | None = None,
    uuid: str | None = None,
    groups: dict[Any, Any] | None = None,
    send_feature_flags: bool = False,
    disable_geoip: bool | None = None,
):
    """
    Capture allows you to capture anything a user does within your system, which you can later use in PostHog to find patterns in usage, work out which features to improve or where people are giving up.

    A `capture` call requires
    - `distinct id` which uniquely identifies your user
    - `event name` to specify the event
    - We recommend using [verb] [noun], like `movie played` or `movie updated` to easily identify what your events mean later on.

    Optionally you can submit
    - `properties`, which can be a dict with any information you'd like to add
    - `groups`, which is a dict of group type -> group key mappings

    For example:
    ```python
    posthog.capture('distinct id', 'opened app')
    posthog.capture('distinct id', 'movie played', {'movie_id': '123', 'category': 'romcom'})

    posthog.capture('distinct id', 'purchase', groups={'company': 'id:5'})
    ```
    """
    posthog.capture(
        distinct_id=distinct_id,
        event=event,
        properties=properties,
        context=context,
        timestamp=timestamp,
        uuid=uuid,
        groups=groups,
        send_feature_flags=send_feature_flags,
        disable_geoip=disable_geoip,
    )


def track_page_visit(page_name: str):
    if current_user.is_authenticated:
        capture_event(
            distinct_id=current_user.email,
            event="page_visited",
            properties={
                "user_id": current_user.email,
                "page": page_name,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    else:
        capture_event(
            distinct_id="anonymous",
            event="page_visited",
            properties={
                "$process_person_profile": False,
                "page": page_name,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


def track_subscription_attempt(subscription_type):
    if current_user.is_authenticated:
        capture_event(
            distinct_id=current_user.email,
            event="subscription_purchase_attempt",
            properties={
                "user_id": current_user.email,
                "subscription_type": subscription_type,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    else:
        capture_event(
            distinct_id="anonymous",
            event="subscription_purchase_attempt",
            properties={
                "$process_person_profile": False,
                "subscription_type": subscription_type,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


def track_subscription_success(subscription_type, user=None):
    if user:
        capture_event(
            distinct_id=user.email,
            event="subscription_purchase_success",
            properties={
                "user_id": user.id,
                "subscription_type": subscription_type,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    else:
        capture_event(
            distinct_id="anonymous",
            event="subscription_purchase_success",
            properties={
                "$process_person_profile": False,
                "subscription_type": subscription_type,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )


def track_subscription_cancellation(subscription_type, user=None):
    if user:
        capture_event(
            distinct_id=user.id,
            event="subscription_cancellation",
            properties={
                "user_id": user.id,
                "subscription_type": subscription_type,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
    else:
        capture_event(
            distinct_id="anonymous",
            event="subscription_cancellation",
            properties={
                "$process_person_profile": False,
                "subscription_type": subscription_type,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
