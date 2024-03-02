from unittest.mock import MagicMock

import pytest
from flask import url_for

from src.project import db, oauth
from src.project.models import User, UserInfo, UserPayment
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

        company = Company(
            name="Test Company",
            description="Test description",
            number_of_employees=10,
            website_url="https://www.example.com",
            country_id=1,
            preferred_round_id=1,
            industry_id=1,
            user=user,
        )
        db.session.add(company)
        db.session.commit()
        return user


def test_user_profile_anonymous_get(client):
    response = client.get("/profile/user/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_user_profile_unverified_get(client, unverified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.get("/profile/user/1", follow_redirects=True)

        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_user_profile_verified_get(client, verified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.get("/profile/user/1", follow_redirects=True)
        assert b"User Profile" in response.data
        assert b"Company Profile" in response.data
        assert b"johndoe@example.com" in response.data
        assert b"John" in response.data
        assert b"Doe" in response.data


def test_company_profile_verified_get(client, verified_user_with_company, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.get("/profile/company/1", follow_redirects=True)
        assert response.status_code == 200
        assert b"User Profile" in response.data
        assert b"Company Profile" in response.data
        assert b"Test Company" in response.data
        assert b"Test description" in response.data


def test_company_profile_anonymous_get(client):
    response = client.get("/profile/company/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_company_profile_unverified_get(client, unverified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.get("/profile/company/1", follow_redirects=True)

        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_company_profile_authenticated_without_company_get(client, verified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.get("/profile/company/1", follow_redirects=True)
        assert response.status_code == 404
