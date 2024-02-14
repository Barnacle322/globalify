import os
import ssl

from flask import current_app
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Email, Mail

ssl._create_default_https_context = ssl._create_unverified_context

SENDER_EMAIL = "info@globalify.xyz"
SENDER_NAME = "Globalify"
SENDGRID_API_KEY = os.environ.get("_SENDGRID_API_KEY")


def send_email(recepients: str | list[str], subject: str, html_content: str) -> None:
    email_credentials = Email(
        email=SENDER_EMAIL,
        name=SENDER_NAME,
    )
    message = Mail(
        from_email=email_credentials,
        to_emails=recepients,
        subject=subject,
        html_content=html_content,
    )

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        current_app.logger.info(f"Email sent to {recepients}")
    except Exception as e:
        current_app.logger.error(f"Email could not be sent to {recepients}")
        current_app.logger.error(e)
        print(e)
