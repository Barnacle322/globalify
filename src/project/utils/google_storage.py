import base64
import io
from uuid import UUID, uuid4

from google.cloud import storage
from PIL import Image


def upload_blob(
    content: bytes,
    old_blob_id: str | None = None,
    bucket_name: str = "globalify_profile_pictures",
    destination_blob_name: UUID = uuid4(),  # noqa: B008
) -> UUID:
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    if old_blob_id:
        blob = bucket.blob(old_blob_id)
        blob.delete()

    blob = bucket.blob(str(destination_blob_name))

    blob.upload_from_file(io.BytesIO(content))

    return destination_blob_name


def download_blob_into_memory(blob_name: UUID, bucket_name: str = "globalify_profile_pictures") -> bytes:
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


def load_pfp(pfp_uuid):
    if not pfp_uuid:
        return False

    try:
        pfp = download_blob_into_memory(pfp_uuid)
        pfp_base64 = base64.b64encode(pfp).decode("utf-8")
    except Exception as e:
        pfp_base64 = False
        print(e)

    return pfp_base64


def upload_pfp(pfp):
    if not pfp:
        return False

    if pfp:
        try:
            resized_pfp = prepare_picture(pfp)
            pfp_uuid = upload_blob(resized_pfp.read())
            return str(pfp_uuid)
        except Exception as e:
            # status = Status(StatusType.ERROR, e.args[0]).get_status()
            # return redirect(url_for("auth.onboarding", _external=False, **status))
            print(e)
            return False
