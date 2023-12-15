import pytest
from werkzeug.security import check_password_hash

from ...project import db
from ...project.models import Company, User, UserInfo, UserPayment
from ...project.utils.status_enum import OauthProvider


@pytest.fixture()
def new_user(app):
    with app.app_context():
        user = User(
            email="johndoe@example.com",
            password="password",
            oauth_provider=OauthProvider.REGULAR,
        )
        db.session.add(user)
        db.session.commit()

        user_info = UserInfo(
            first_name="John",
            last_name="Doe",
            user=user,
        )
        user_payment = UserPayment(
            customer_id="cus_123",
            user=user,
        )
        db.session.add_all([user_info, user_payment])
        db.session.commit()


@pytest.fixture()
def new_company(app):
    with app.app_context():
        company = Company(
            name="Globalify",
            user_id=1,
            description="A very cool company",
            number_of_employees=3,
            website="https://globalify.xyz",
            country_id=235,
            preferred_round_id=1,
            industry_id=1,
        )
        db.session.add(company)
        db.session.commit()


def test_user(new_user, app):
    with app.app_context():
        user = User.query.first()

        assert user
        assert user.email == "johndoe@example.com"
        assert check_password_hash(user.password_hash, "password")
        assert user.oauth_provider == OauthProvider.REGULAR
        assert user.is_verified is False
        assert user.is_admin is False


def test_user_info(new_user, app):
    with app.app_context():
        user_info = UserInfo.query.first()

        assert user_info
        assert user_info.first_name == "John"
        assert user_info.last_name == "Doe"


def test_user_payment(new_user, app):
    with app.app_context():
        user_payment = UserPayment.query.first()

        assert user_payment
        assert user_payment.customer_id == "cus_123"


def test_company(new_company, app):
    with app.app_context():
        company = Company.query.first()

        assert company
        assert company.name == "Globalify"
        assert company.user_id == 1
        assert company.description == "A very cool company"
        assert company.number_of_employees == 3
        assert company.website == "https://globalify.xyz"
        assert company.country_id == 235
        assert company.preferred_round_id == 1
        assert company.industry_id == 1
