import os

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Email, Mail

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
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print("⚠️  Email could not be sent.")
        print(e)
