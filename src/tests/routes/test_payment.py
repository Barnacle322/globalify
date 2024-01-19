from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from src.project.models.user import User, UserInfo, UserPayment, UserRegular
from src.project.routes.payment import get_invoices, handle_customer
from src.project.utils.errors.auth_error_messages import ONBOARDING_INCOMPLETE

from ...project import db


@pytest.fixture()
def user(app):
    with app.app_context():
        user = UserRegular(
            email="johndoe@example.com",
            password="password",
        )
        db.session.add(user)
        db.session.commit()

        user_info = UserInfo(
            first_name="John",
            last_name="Doe",
            username="johndoe",
            is_complete=False,
            user=user,
        )
        user_payment = UserPayment(
            customer_id="",
            user=user,
        )
        db.session.add_all([user_info, user_payment])
        db.session.commit()


def test_get_invoices_incomplete_onboarding(user, app):
    with pytest.raises(Exception) as exc_info:
        with app.app_context():
            get_invoices(User.get_by_id(1))  # type: ignore
    assert str(exc_info.value) == ONBOARDING_INCOMPLETE


def test_get_invoices_payment_incomplete(user, app):
    with app.app_context():
        UserInfo.get_by_user_id(1).is_complete = True  # type: ignore
        db.session.commit()
        invoices = get_invoices(User.get_by_id(1))  # type: ignore
    assert invoices == []


def test_get_invoices_success(user, app):
    with app.app_context():
        UserInfo.get_by_user_id(1).is_complete = True  # type: ignore
        UserPayment.get_by_user_id(1).customer_id = "cus_123"  # type: ignore
        db.session.commit()
        stripe_invoice_data = [
            {
                "id": "inv_test",
                "created": int(datetime.utcnow().timestamp()),
                "amount_due": 1000,
                "amount_paid": 1000,
                "currency": "usd",
                "status": "paid",
                "hosted_invoice_url": "https://invoice.url",
            }
        ]
        stripe_invoices = Mock(auto_spec=True)
        stripe_invoices.list.return_value = stripe_invoice_data
        with patch("stripe.Invoice", stripe_invoices):
            invoices = get_invoices(User.get_by_id(1))  # type: ignore
            assert invoices[0]["id"] == "inv_test"
            assert invoices[0]["amount_due"] == 1000
            assert invoices[0]["status"] == "paid"


def test_handle_customer(user, app):
    with pytest.raises(Exception) as exc_info:
        with app.app_context():
            handle_customer(User.get_by_id(1))  # type: ignore
    assert str(exc_info.value) == ONBOARDING_INCOMPLETE
