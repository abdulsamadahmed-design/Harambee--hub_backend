
import os
import logging

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)


def send_verification_email(to_email, verification_url):
    """
    Send an email verification link using SendGrid.

    Returns True if SendGrid accepts the email.
    Returns False if configuration or delivery fails.
    """

    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL")

    if not api_key or not from_email:
        logger.error("SendGrid configuration is missing.")
        return False

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject="Verify your Harambee Hub account",
        plain_text_content=(
            "Welcome to Harambee Hub!\n\n"
            "Please verify your email address by clicking "
            "the link below:\n\n"
            f"{verification_url}\n\n"
            "If you did not create this account, ignore this email."
        )
    )

    try:
        client = SendGridAPIClient(api_key)
        response = client.send(message)

        if 200 <= response.status_code < 300:
            logger.info("Verification email accepted by SendGrid.")
            return True

        logger.warning(
            "SendGrid rejected the email. Status: %s",
            response.status_code
        )
        return False

    except Exception as error:
        logger.error(
            "Verification email delivery failed: %s",
            type(error).__name__
        )
        return False
