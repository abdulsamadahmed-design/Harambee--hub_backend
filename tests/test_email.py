
from app.utils.email import send_verification_email


def test_email_fails_when_configuration_is_missing(monkeypatch):
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.delenv("SENDGRID_FROM_EMAIL", raising=False)

    result = send_verification_email(
        "test@example.com",
        "http://localhost/verify"
    )

    assert result is False


def test_email_fails_when_sendgrid_raises_exception(monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "test-api-key")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "sender@example.com")

    class FakeSendGridClient:
        def __init__(self, api_key):
            pass

        def send(self, message):
            raise Exception("SendGrid connection failed")

    monkeypatch.setattr(
        "app.utils.email.SendGridAPIClient",
        FakeSendGridClient
    )

    result = send_verification_email(
        "test@example.com",
        "http://localhost/verify"
    )

    assert result is False
