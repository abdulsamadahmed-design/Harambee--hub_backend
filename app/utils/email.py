import os
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)


def send_email(to_email, subject, body):
    """Send a general email using SendGrid."""

    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL")

    if not api_key or not from_email:
        logger.error("SendGrid configuration is missing.")
        return False

    if not to_email:
        logger.error("Recipient email is missing.")
        return False

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject=subject,
        plain_text_content=body
    )

    try:
        client = SendGridAPIClient(api_key)
        response = client.send(message)

        if 200 <= response.status_code < 300:
            logger.info("Email accepted by SendGrid.")
            return True

        logger.warning(
            "SendGrid rejected the email. Status: %s",
            response.status_code
        )
        return False

    except Exception as error:
        logger.error(
            "Email delivery failed: %s",
            type(error).__name__
        )
        return False


def send_verification_email(to_email, verification_url):
    """Send an email verification link using SendGrid."""

    body = (
        "Welcome to Harambee Hub!\n\n"
        "Please verify your email address by clicking "
        "the link below:\n\n"
        f"{verification_url}\n\n"
        "If you did not create this account, ignore this email."
    )

    return send_email(
        to_email,
        "Verify your Harambee Hub account",
        body
    )
