import os

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Email, Mail


def send_email(recepients: str | list[str], subject: str, html_content: str) -> None:
    email = Email(
        email="info@globalify.xyz",
        name="Globalify",
    )
    message = Mail(
        from_email=email,
        to_emails=recepients,
        subject=subject,
        html_content=html_content,
    )

    try:
        sg = SendGridAPIClient(os.environ.get("_SENDGRID_API_KEY"))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print("⚠️  Email could not be sent.")
        print(e)
