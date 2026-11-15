import os
from pathlib import Path

import cloudinary
import cloudinary.uploader


MAX_IMAGE_SIZE = 5 * 1024 * 1024

IMAGE_SIGNATURES = {
    "JPEG": lambda data: data.startswith(b"\xff\xd8\xff"),
    "PNG": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
    "WebP": lambda data: (
        len(data) >= 12
        and data[:4] == b"RIFF"
        and data[8:12] == b"WEBP"
    ),
}

IMAGE_EXTENSIONS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "WebP": {".webp"},
}


def validate_image(image_file):
    """Validate image size, filename extension and file signature."""

    if not image_file or not hasattr(image_file, "stream"):
        raise ValueError("A valid image file is required.")

    filename = getattr(image_file, "filename", None)

    if not filename:
        raise ValueError("Image filename is required.")

    extension = Path(filename).suffix.lower()

    stream = image_file.stream

    try:
        stream.seek(0, os.SEEK_END)
        file_size = stream.tell()
        stream.seek(0)

        if file_size == 0:
            raise ValueError("The image file is empty.")

        if file_size > MAX_IMAGE_SIZE:
            raise ValueError("Image must not exceed 5 MB.")

        header = stream.read(12)
        stream.seek(0)

    except (AttributeError, OSError):
        raise ValueError("Unable to read the image file.")

    detected_format = next(
        (
            image_format
            for image_format, check in IMAGE_SIGNATURES.items()
            if check(header)
        ),
        None
    )

    if detected_format is None:
        raise ValueError("Only JPEG, PNG and WebP images are allowed.")

    if extension not in IMAGE_EXTENSIONS[detected_format]:
        raise ValueError("Image filename extension does not match its content.")


def upload_image(image_file):
    """Validate an image, upload it to Cloudinary and return its secure URL."""

    validate_image(image_file)

    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        raise RuntimeError("Cloudinary credentials are not configured.")

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True
    )

    result = cloudinary.uploader.upload(
        image_file,
        folder="harambee_campaigns",
        resource_type="image"
    )

    return result["secure_url"]
