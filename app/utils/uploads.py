
import os
import cloudinary
import cloudinary.uploader


def upload_image(image_file):
    """
    Upload an image to Cloudinary and return its secure URL.
    """

    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True
    )

    if not all([
        os.getenv("CLOUDINARY_CLOUD_NAME"),
        os.getenv("CLOUDINARY_API_KEY"),
        os.getenv("CLOUDINARY_API_SECRET")
    ]):
        raise RuntimeError("Cloudinary credentials are not configured.")

    result = cloudinary.uploader.upload(
        image_file,
        folder="harambee_campaigns",
        resource_type="image"
    )

    return result["secure_url"]
