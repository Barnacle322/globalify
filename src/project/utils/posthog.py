import os
from datetime import datetime

import posthog
from flask import g
from flask_login import current_user

posthog.api_key = os.getenv("_POSTHOG_API_KEY")
posthog.host = "https://us.i.posthog.com"


def capture_event(
    distinct_id: str,
    event: str,
    properties: dict | None = None,
    context: dict | None = None,
    timestamp: datetime | None = None,
    uuid: str | None = None,
    groups: dict | None = None,
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
    capture_event(distinct_id='distinct id', event='opened app')
    capture_event(distinct_id='distinct id', event='movie played', {'movie_id': '123', 'category': 'romcom'})

    capture_event(distinct_id='distinct id', event='purchase', groups={'company': 'id:5'})
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


def capture_page_visit(page_name: str):
    if current_user.is_authenticated:
        capture_event(
            distinct_id=current_user.email,
            event="$pageview",
            properties={
                "page": page_name,
            },
        )
    else:
        capture_event(
            distinct_id=g.anonymous_id,
            event="$pageview",
            properties={
                "$process_person_profile": False,
                "page": page_name,
            },
        )


def capture_profile_view(profile_type: str, properties: dict):
    if current_user.is_authenticated:
        capture_event(
            distinct_id=current_user.email,
            event=f"{profile_type}_profile_view",
            properties=properties,
        )
    else:
        capture_event(
            distinct_id=g.anonymous_id,
            event=f"{profile_type}_profile_view",
            properties={**properties, "$process_person_profile": False},
        )
