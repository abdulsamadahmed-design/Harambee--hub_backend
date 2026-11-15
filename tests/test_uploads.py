from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from app.utils import uploads


def make_image(content, filename):
    return FileStorage(
        stream=BytesIO(content),
        filename=filename
    )


def set_cloudinary_credentials(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_CLOUD_NAME", "test-cloud")
    monkeypatch.setenv("CLOUDINARY_API_KEY", "test-key")
    monkeypatch.setenv("CLOUDINARY_API_SECRET", "test-secret")


def test_upload_image_rejects_missing_credentials(monkeypatch):
    monkeypatch.delenv("CLOUDINARY_CLOUD_NAME", raising=False)
    monkeypatch.delenv("CLOUDINARY_API_KEY", raising=False)
    monkeypatch.delenv("CLOUDINARY_API_SECRET", raising=False)

    image = make_image(b"\xff\xd8\xff" + b"test image", "photo.jpg")

    with pytest.raises(
        RuntimeError,
        match="Cloudinary credentials are not configured"
    ):
        uploads.upload_image(image)


def test_upload_image_uploads_and_returns_secure_url(monkeypatch):
    set_cloudinary_credentials(monkeypatch)

    image = make_image(b"\xff\xd8\xff" + b"test image", "photo.jpg")

    config_calls = []
    upload_calls = []

    def fake_config(**kwargs):
        config_calls.append(kwargs)

    def fake_upload(image_file, **kwargs):
        upload_calls.append((image_file, kwargs))
        return {"secure_url": "https://example.com/image.jpg"}

    monkeypatch.setattr(uploads.cloudinary, "config", fake_config)
    monkeypatch.setattr(uploads.cloudinary.uploader, "upload", fake_upload)

    result = uploads.upload_image(image)

    assert result == "https://example.com/image.jpg"
    assert config_calls == [{
        "cloud_name": "test-cloud",
        "api_key": "test-key",
        "api_secret": "test-secret",
        "secure": True,
    }]
    assert upload_calls == [(
        image,
        {
            "folder": "harambee_campaigns",
            "resource_type": "image",
        },
    )]


def test_upload_image_propagates_cloudinary_failure(monkeypatch):
    set_cloudinary_credentials(monkeypatch)

    image = make_image(b"\xff\xd8\xff" + b"test image", "photo.jpg")

    monkeypatch.setattr(
        uploads.cloudinary,
        "config",
        lambda **kwargs: None
    )

    def fake_upload(*args, **kwargs):
        raise RuntimeError("Cloudinary is unavailable")

    monkeypatch.setattr(
        uploads.cloudinary.uploader,
        "upload",
        fake_upload
    )

    with pytest.raises(RuntimeError, match="Cloudinary is unavailable"):
        uploads.upload_image(image)


@pytest.mark.parametrize(
    "content,filename",
    [
        (b"\x89PNG\r\n\x1a\n" + b"test image", "photo.png"),
        (b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"test image", "photo.webp"),
        (b"\xff\xd8\xff" + b"test image", "photo.jpeg"),
    ],
)
def test_validate_image_accepts_supported_formats(content, filename):
    image = make_image(content, filename)

    uploads.validate_image(image)


def test_validate_image_rejects_invalid_content():
    image = make_image(b"not an image", "photo.jpg")

    with pytest.raises(ValueError, match="Only JPEG, PNG and WebP"):
        uploads.validate_image(image)


def test_validate_image_rejects_empty_file():
    image = make_image(b"", "empty.jpg")

    with pytest.raises(ValueError, match="empty"):
        uploads.validate_image(image)


def test_validate_image_rejects_files_over_5mb():
    image = make_image(b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024), "large.jpg")

    with pytest.raises(ValueError, match="must not exceed 5 MB"):
        uploads.validate_image(image)


def test_validate_image_restores_file_position():
    image = make_image(b"\xff\xd8\xff" + b"test image", "photo.jpg")

    uploads.validate_image(image)

    assert image.stream.tell() == 0


def test_validate_image_rejects_mismatched_extension():
    image = make_image(
        b"\x89PNG\r\n\x1a\n" + b"test image",
        "photo.jpg"
    )

    with pytest.raises(
        ValueError,
        match="extension does not match"
    ):
        uploads.validate_image(image)
