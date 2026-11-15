
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


def test_email_fails_when_recipient_is_missing(monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "test-api-key")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "sender@example.com")

    from app.utils.email import send_email

    assert send_email("", "Test subject", "Test body") is False


def test_email_succeeds_when_sendgrid_accepts_message(monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "test-api-key")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "sender@example.com")

    class FakeResponse:
        status_code = 202

    class FakeSendGridClient:
        def __init__(self, api_key):
            assert api_key == "test-api-key"

        def send(self, message):
            return FakeResponse()

    monkeypatch.setattr(
        "app.utils.email.SendGridAPIClient",
        FakeSendGridClient
    )

    from app.utils.email import send_email

    assert send_email(
        "recipient@example.com",
        "Test subject",
        "Test body"
    ) is True


def test_email_fails_when_sendgrid_rejects_message(monkeypatch):
    monkeypatch.setenv("SENDGRID_API_KEY", "test-api-key")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "sender@example.com")

    class FakeResponse:
        status_code = 400

    class FakeSendGridClient:
        def __init__(self, api_key):
            pass

        def send(self, message):
            return FakeResponse()

    monkeypatch.setattr(
        "app.utils.email.SendGridAPIClient",
        FakeSendGridClient
    )

    from app.utils.email import send_email

    assert send_email(
        "recipient@example.com",
        "Test subject",
        "Test body"
    ) is False


def test_verification_email_uses_correct_subject_and_body(monkeypatch):
    from app.utils import email

    captured = {}

    def fake_send_email(to_email, subject, body):
        captured["to_email"] = to_email
        captured["subject"] = subject
        captured["body"] = body
        return True

    monkeypatch.setattr(email, "send_email", fake_send_email)

    result = email.send_verification_email(
        "recipient@example.com",
        "https://example.com/verify"
    )

    assert result is True
    assert captured["to_email"] == "recipient@example.com"
    assert captured["subject"] == "Verify your Harambee Hub account"
    assert "https://example.com/verify" in captured["body"]
