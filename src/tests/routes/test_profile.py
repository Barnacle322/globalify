import pytest
from flask_login import login_user

from src.project import db
from src.project.models import User, UserCompany, UserInfo, UserPayment
from src.project.models.user import Company
from src.project.utils.enums import OauthProvider


@pytest.fixture()
def verified_user(app):
    with app.app_context():
        user = User(
            oauth_provider=OauthProvider.GOOGLE,
            email="johndoe@example.com",
            is_verified=True,
        )
        db.session.add(user)
        db.session.commit()

        user_info = UserInfo(
            first_name="John",
            last_name="Doe",
            username="johndoe",
            is_complete=True,
            user=user,
        )
        user_payment = UserPayment(
            customer_id="cus_123",
            user=user,
        )
        db.session.add_all([user_info, user_payment])
        db.session.commit()
        return user


@pytest.fixture()
def unverified_user(app):
    with app.app_context():
        user = User(
            oauth_provider=OauthProvider.GOOGLE,
            email="johndoe@example.com",
        )
        db.session.add(user)
        db.session.commit()

        user_info = UserInfo(
            first_name="John",
            last_name="Doe",
            username="johndoe",
            is_complete=True,
            user=user,
        )
        user_payment = UserPayment(
            customer_id="cus_123",
            user=user,
        )
        db.session.add_all([user_info, user_payment])
        db.session.commit()
        return user


@pytest.fixture()
def verified_user_with_company(app):
    with app.app_context():
        user = User(
            oauth_provider=OauthProvider.GOOGLE,
            email="johndoe@example.com",
            is_verified=True,
        )
        db.session.add(user)
        db.session.commit()

        user_info = UserInfo(
            first_name="John",
            last_name="Doe",
            username="johndoe",
            is_complete=True,
            user=user,
        )
        user_payment = UserPayment(
            customer_id="cus_123",
            user=user,
        )
        db.session.add_all([user_info, user_payment])
        db.session.commit()

        company = Company(name="Test Company")

        company.description = "Test description"
        company.number_of_employees = 10
        company.website_url = "https://www.example.com"
        company.country_id = 1
        company.preferred_round_id = 1
        company.industry_id = 1

        db.session.add(company)
        db.session.commit()

        user_company = UserCompany(1, 1, is_primary=True, is_public=True)

        db.session.add(user_company)
        db.session.commit()

        return user


def test_user_profile_anonymous_get(client):
    response = client.get("/profile/johndoe", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_user_profile_unverified_get(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/profile/johndoe", follow_redirects=True)

        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_profile_verified_get(client, app, verified_user_with_company, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/profile/johndoe", follow_redirects=True)
        assert response.status_code == 200
        assert b"Test Company" in response.data
        assert b"Test description" in response.data


def test_company_profile_anonymous_get(client):
    response = client.get("/profile/johndoe", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_company_profile_unverified_get(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/profile/johndoe", follow_redirects=True)

        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_company_profile_authenticated_without_company_get(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/profile/johndasdadoee")
        assert response.status_code == 302
