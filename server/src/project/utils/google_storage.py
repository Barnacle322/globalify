import io
from uuid import UUID, uuid4

from google.cloud import storage
from PIL import Image


def upload_blob(
    content: bytes, bucket_name: str = "globalify_profile_pictures"
) -> UUID:
    destination_blob_name = uuid4()

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(str(destination_blob_name))

    blob.upload_from_file(io.BytesIO(content))

    return destination_blob_name


def download_blob_into_memory(
    blob_name: UUID, bucket_name: str = "globalify_profile_pictures"
) -> bytes:
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(blob_name)
    contents = blob.download_as_string()

    return contents


def prepare_picture(image):
    input_image = Image.open(io.BytesIO(image.read()))

    width, height = input_image.size
    size = min(width, height)
    left = (width - size) // 2
    top = (height - size) // 2
    right = left + size
    bottom = top + size

    square_image = input_image.crop((left, top, right, bottom))
    square_image.thumbnail((100, 100))

    resized_pfp = io.BytesIO()
    square_image.save(resized_pfp, format="JPEG")
    resized_pfp.seek(0)

    return resized_pfp
