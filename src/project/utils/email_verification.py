import datetime

from ..extensions import db
from ..models.user import EmailVerification


def update_is_expired(email_verification: EmailVerification):
    """
    Update the is_expired field of the email_verification object
    based on the current time.

    Args:
        email_verification (EmailVerification): The email_verification object to update.
    """
    if not email_verification.is_expired:
        expiration_time = email_verification.created_at + datetime.timedelta(minutes=5)

        if datetime.datetime.now(datetime.UTC) > expiration_time.replace(tzinfo=datetime.UTC):
            email_verification.is_expired = True
            db.session.commit()


def create_verification_token(user_id: int) -> str:
    """
    Create a verification token and store it in the EmailVerification table.

    Args:
        user_id (int): The ID of the user for whom the verification token is being created.

    Returns:
        str: The generated verification token.
    """
    verification = EmailVerification(user_id=user_id)
    db.session.add(verification)
    db.session.commit()
    return verification.token
