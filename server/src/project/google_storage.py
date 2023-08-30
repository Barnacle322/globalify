import io
from uuid import UUID, uuid4

from google.cloud import storage


def upload_blob(content: bytes) -> UUID:
    bucket_name = "globalify_profile_pictures"
    destination_blob_name = uuid4()

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(str(destination_blob_name))

    blob.upload_from_file(io.BytesIO(content))

    return destination_blob_name


def download_blob_into_memory(blob_name: UUID) -> bytes:
    bucket_name = "globalify_profile_pictures"
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(blob_name)
    contents = blob.download_as_string()

    return contents
