"""Publishes multiple messages to a Pub/Sub topic with an error handler."""
import os
from collections.abc import Callable
from concurrent import futures

from google.cloud import pubsub_v1

credentials = {
    "type": os.environ.get("_PUBSUB_TYPE"),
    "project_id": os.environ.get("_PUBSUB_PROJECT_ID"),
    "private_key_id": os.environ.get("_PUBSUB_PRIVATE_KEY_ID"),
    "private_key": os.environ.get("_PUBSUB_PRIVATE_KEY", "").replace("\\n", "\n"),
    "client_email": os.environ.get("_PUBSUB_CLIENT_EMAIL"),
    "client_id": os.environ.get("_PUBSUB_CLIENT_ID"),
    "auth_uri": os.environ.get("_PUBSUB_AUTH_URI"),
    "token_uri": os.environ.get("_PUBSUB_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.environ.get("_PUBSUB_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.environ.get("_PUBSUB_CLIENT_X509_CERT_URL"),
    "universe_domain": os.environ.get("_PUBSUB_UNIVERSE_DOMAIN"),
}


project_id = "globalify-email-service"
topic_id = "test_topic"

publisher = pubsub_v1.PublisherClient().from_service_account_info(credentials)
topic_path = publisher.topic_path(project_id, topic_id)
publish_futures = []


def get_callback(
    publish_future: pubsub_v1.publisher.futures.Future,  # type: ignore
    data: str,
) -> Callable[[pubsub_v1.publisher.futures.Future], None]:  # type: ignore
    def callback(publish_future: pubsub_v1.publisher.futures.Future) -> None:  # type: ignore
        try:
            # Wait 60 seconds for the publish call to succeed.
            print(publish_future.result(timeout=60))
        except futures.TimeoutError:
            print(f"Publishing {data} timed out.")

    return callback


for i in range(10):
    data = str(i)
    # When you publish a message, the client returns a future.
    publish_future = publisher.publish(topic_path, data.encode("utf-8"))
    # Non-blocking. Publish failures are handled in the callback function.
    publish_future.add_done_callback(get_callback(publish_future, data))
    publish_futures.append(publish_future)

# Wait for all the publish futures to resolve before exiting.
futures.wait(publish_futures, return_when=futures.ALL_COMPLETED)

print(f"Published messages with error handler to {topic_path}.")
