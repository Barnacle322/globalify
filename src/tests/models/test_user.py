import datetime

import pytest
from freezegun import freeze_time

from ...project import db
from ...project.models import Company, User, UserInfo, UserPayment
from ...project.utils.enums import OauthProvider, Tier


@pytest.fixture()
def new_user_oauth(app):
    with app.app_context():
        user = User(email="janedoe@example.com", oauth_provider=OauthProvider.GOOGLE)
        db.session.add(user)
        db.session.commit()

        user_info = UserInfo(
            first_name="Jane",
            last_name="Doe",
            username="janedoe",
            user=user,
            linkedin_url="https://linkedin.com/in/janedoe",
            twitter_url="https://twitter.com/janedoe",
            instagram_url="https://instagram.com/janedoe",
            bio="I'm a cool person",
        )
        user_payment = UserPayment(
            customer_id="cus_123",
            subscription_id="sub_123",
            is_active=True,
            tier=Tier.FREE,
            user=user,
        )
        user_payment.created_epoch = 1609462861
        user_payment.expires_at_epoch = 1612141261

        db.session.add_all([user_info, user_payment])
        db.session.commit()


@pytest.fixture()
def new_company(app):
    with app.app_context():
        company = Company(user_id=1, name="Globalify")

        company.description = "A very cool company"
        company.number_of_employees = 3
        company.website_url = "https://globalify.xyz"
        company.picture_url = "https://www.example.com"
        company.country_id = 235
        company.preferred_round_id = 1
        company.industry_id = 1
        db.session.add(company)
        db.session.commit()


def test_empty_db(app):
    with app.app_context():
        users = User.get_all()
        assert isinstance(users, list)
        assert len(users) == 0

        user = User.get_by_email("johndoe@example.com")
        assert user is None

        user = User.get_by_id(1)
        assert user is None

        company = Company.get_by_id(1)
        assert company is None

        company = Company.get_by_user_id(1)
        assert company is None


def test_user_oauth(new_user_oauth, app):
    with app.app_context():
        user = User.get_by_email("janedoe@example.com")
        users = User.get_all()

        assert users and len(users) == 1
        assert user and isinstance(user, User)

        assert user.oauth_provider == OauthProvider.GOOGLE
        assert user.is_verified is False
        assert user.is_admin is False


def test_user_info(new_user_oauth, app):
    with app.app_context():
        user_info = UserInfo.get_by_user_id(1)
        user_infos = UserInfo.get_all()

        assert user_info
        assert user_infos and len(user_infos) == 1

        assert user_info.first_name == "Jane"
        assert user_info.last_name == "Doe"
        assert user_info.username == "janedoe"
        assert user_info.linkedin_url == "https://linkedin.com/in/janedoe"
        assert user_info.twitter_url == "https://twitter.com/janedoe"
        assert user_info.instagram_url == "https://instagram.com/janedoe"
        assert user_info.bio == "I'm a cool person"
        assert user_info.picture_url is None

        assert UserInfo.is_taken("janedoe")
        assert not UserInfo.is_taken("johndoe")
        assert user_info.sanitize() == {
            "user_id": 1,
            "username": "janedoe",
            "first_name": "Jane",
            "last_name": "Doe",
            "linkedin": "https://linkedin.com/in/janedoe",
            "instagram": "https://instagram.com/janedoe",
            "twitter": "https://twitter.com/janedoe",
            "bio": "I'm a cool person",
            "pfp": None,
        }


@freeze_time("2021-01-02")
def test_user_payment(new_user_oauth, app):
    with app.app_context():
        user_payment = UserPayment.get_by_customer_id("cus_123")
        assert user_payment
        user_payment = UserPayment.get_by_user_id(1)
        assert user_payment
        assert user_payment.customer_id == "cus_123"
        assert user_payment.subscription_id == "sub_123"
        assert user_payment.created == datetime.datetime(2021, 1, 1, 1, 1, 1)
        assert user_payment.expires_at == datetime.datetime(2021, 2, 1, 1, 1, 1)
        assert user_payment.is_active is True
        assert user_payment.tier == Tier.FREE

        assert user_payment.is_expired() is False
        assert user_payment.sanitize() == {
            "created": datetime.datetime(2021, 1, 1, 1, 1, 1),
            "expires_at": datetime.date(2021, 2, 1),
            "is_active": True,
            "tier": Tier.FREE,
            "subscription_id": "sub_123",
        }


@freeze_time("2021-03-01")
def test_user_payment_expired(new_user_oauth, app):
    with app.app_context():
        user_payment = UserPayment.query.first()
        assert user_payment
        assert user_payment.is_expired() is True


def test_company(new_user_oauth, new_company, app):
    with app.app_context():
        company = Company.get_by_id(1)
        assert company
        company = Company.get_by_user_id(1)
        assert company
        assert company.name == "Globalify"
        assert company.user_id == 1
        assert company.description == "A very cool company"
        assert company.number_of_employees == 3
        assert company.website_url == "https://globalify.xyz"
        assert company.country_id == 235
        assert company.preferred_round_id == 1
        assert company.industry_id == 1
