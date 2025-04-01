import base64
import io
from uuid import UUID, uuid4

from google.cloud import storage
from PIL import Image
from pillow_heif import register_heif_opener

HD_WIDTH = 1280
HD_HEIGHT = 720
BUCKET_NAME = "globalify_profile_pictures"


register_heif_opener()


def delete_blob_from_url(blob_url: str, bucket_name: str = BUCKET_NAME) -> None:
    # Extract the blob name from the URL
    if f"https://storage.googleapis.com/{bucket_name}/" in blob_url:
        blob_name = blob_url.replace(f"https://storage.googleapis.com/{bucket_name}/", "")
    else:
        raise ValueError("Invalid blob URL")

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.delete()


def upload_blob(
    content: bytes,
    content_type: str,
    destination_blob_name: UUID | None = None,
    old_blob_id: str | None = None,
    blob_name: str | None = None,
    bucket_name: str = BUCKET_NAME,
) -> str:
    if not destination_blob_name:
        destination_blob_name = uuid4()

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(str(destination_blob_name))

    # Set the content type of the blob
    blob.content_type = content_type

    if blob_name:
        blob.name = blob_name

    try:
        blob.upload_from_file(io.BytesIO(content), content_type=content_type)
    except Exception as e:
        print(e)
        raise

    if old_blob_id:
        old_blob = bucket.blob(old_blob_id)
        old_blob.delete()

    return blob.public_url


def download_blob_into_memory(blob_name: UUID, bucket_name: str = BUCKET_NAME) -> bytes:
    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(blob_name)
    contents = blob.download_as_string()

    return contents


def prepare_picture(image):
    input_image = Image.open(io.BytesIO(image.read()))
    # Convert RGBA images to RGB mode
    if input_image.mode == "RGBA":
        background = Image.new("RGB", input_image.size, (255, 255, 255))
        background.paste(input_image, mask=input_image.split()[3])
        input_image = background.convert("RGB")

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


def scale_to_hd(image: io.IOBase) -> io.BytesIO:
    input_image = Image.open(io.BytesIO(image.read()))

    # Convert RGBA images to RGB mode
    if input_image.mode == "RGBA":
        background = Image.new("RGB", input_image.size, (255, 255, 255))
        background.paste(input_image, mask=input_image.split()[3])
        input_image = background.convert("RGB")

    width, height = input_image.size

    # Only scale if the image is larger than HD
    if width > HD_WIDTH or height > HD_HEIGHT:
        # Calculate the aspect ratio
        aspect_ratio = width / height

        # Calculate new dimensions
        if aspect_ratio > 1:
            new_width = HD_WIDTH
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = HD_HEIGHT
            new_width = int(new_height * aspect_ratio)

        # Resize the image
        input_image = input_image.resize((new_width, new_height))

    # Save the image to a BytesIO object
    output_image = io.BytesIO()
    input_image.save(output_image, format="JPEG")
    output_image.seek(0)

    return output_image


def load_picture(picture_uuid):
    if not picture_uuid:
        return False

    try:
        picture = download_blob_into_memory(picture_uuid)
        picture_base64 = base64.b64encode(picture).decode("utf-8")
    except Exception as e:
        print(e)
        raise

    return picture_base64


def upload_picture(picture, bucket_name: str = BUCKET_NAME):
    if not picture or picture == "" or picture == "None":
        raise ValueError("No picture provided")

    try:
        resized_picture = prepare_picture(picture)
        picture_url = upload_blob(resized_picture.read(), bucket_name=bucket_name, content_type="image/jpeg")
        return picture_url
    except Exception as e:
        print(e)
        raise


def load_deck(deck_uuid):
    if not deck_uuid:
        return False

    try:
        deck = download_blob_into_memory(deck_uuid)
        deck_base64 = base64.b64encode(deck).decode("utf-8")
    except Exception as e:
        print(e)
        raise

    return deck_base64


def upload_deck(deck, blob_name, content_type, bucket_name: str = BUCKET_NAME):
    if not deck or deck == "" or deck == "None":
        raise ValueError("No deck provided")

    try:
        deck_url = upload_blob(deck, blob_name=blob_name, bucket_name=bucket_name, content_type=content_type)
        return deck_url
    except Exception as e:
        print(e)
        raise
