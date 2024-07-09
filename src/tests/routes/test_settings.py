from unittest.mock import MagicMock, patch

import pytest
from flask import url_for
from flask_login import login_user

from src.project import db
from src.project.extensions import oauth
from src.project.models import User, UserInfo, UserPayment
from src.project.models.user import Company
from src.project.utils import suggestion
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
def username_taken_user(app):
    with app.app_context():
        user = User(
            oauth_provider=OauthProvider.GOOGLE,
            email="angelina@example.com",
            is_verified=True,
        )
        db.session.add(user)
        db.session.commit()

        user_info = UserInfo(
            first_name="Angelina",
            last_name="Jolie",
            username="AngelinaJolie",
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
def new_user_with_company(app):
    with app.app_context():
        user = User(
            oauth_provider=OauthProvider.GOOGLE,
            email="margarita@example.com",
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
        db.session.add(user_info)
        db.session.commit()

        company = Company(user_id=1, name="Test Company")

        company.description = "Test description"
        company.number_of_employees = 10
        company.website_url = "https://www.example.com"
        company.picture_url = "https://www.example.com"
        company.country_id = 1
        company.preferred_round_id = 1
        company.industry_id = 1

        db.session.add(company)
        db.session.commit()
        return user


def test_settings_anonymous_get(client):
    response = client.get("/settings/general", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_unverified_get(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/general", follow_redirects=True)
        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_settings_verified_get(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/general")
        assert response.status_code == 200
        assert b"Personal Information" in response.data
        assert b"Use a permanent address where you can receive mail." in response.data


def test_settings_security_anonymous_get(client):
    response = client.get("/settings/security", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_security_unverified_get(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_settings_security_verified_get(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/security")
        assert response.status_code == 200
        assert b"Delete account" in response.data
        assert (
            b"No longer want to use our service? You can delete your account here. This action is not reversible."
            in response.data
        )
        assert b"Yes, delete my account" in response.data


def test_settings_plan_anonymous_get(client):
    response = client.get("/settings/plan", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_plan_unverified_get(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/plan", follow_redirects=True)
        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_settings_plan_verified_get(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/plan")
        assert response.status_code == 200
        assert b"Your subscription" in response.data
        assert b"You have free access to some Globalify features" in response.data
        # assert b"This is your current subscription. You can update your plan any time." in response.data


def test_settings_billing_anonymous_get(client):
    response = client.get("/settings/plan", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_billing_unverified_get(client, app, unverified_user, monkeypatch):
    with patch("stripe.Invoice.list") as mock_invoice_list:
        mock_invoice_list.return_value = [
            {
                "id": "invoice_123",
                "created": 1642370100,
                "amount_due": 1000,
                "amount_paid": 500,
                "currency": "usd",
                "status": "paid",
                "hosted_invoice_url": "https://example.com/invoice/123",
            }
        ]
        with app.test_request_context():
            user = User.get_by_id(1)
            login_user(user)

            response = client.get("/settings/billing", follow_redirects=True)

            assert response.status_code == 200
            assert b"Email Verification" in response.data
            assert (
                b"A verification email has been sent to you! Click the link or input a code to verify your email address."
                in response.data
            )
            assert b"Verify" in response.data


def test_settings_billing_verified_get(client, app, verified_user, monkeypatch):
    with patch("stripe.Invoice.list") as mock_invoice_list:
        mock_invoice_list.return_value = [
            {
                "id": "invoice_123",
                "created": 1642370100,
                "amount_due": 1000,
                "amount_paid": 500,
                "currency": "usd",
                "status": "paid",
                "hosted_invoice_url": "https://example.com/invoice/123",
            }
        ]
        with app.test_request_context():
            user = User.get_by_id(1)
            login_user(user)

            response = client.get("/settings/billing", follow_redirects=True)

            assert response.status_code == 200
            assert b"Manage billing" in response.data
            assert b"Manage your billing details with" in response.data
            assert b"See your invoice history here." in response.data


def test_anonymous_user_change_personal_info(client, app, monkeypatch):
    with app.app_context():
        response = client.post(
            "/settings/personal-info",
            data={
                "first-name": "NewFirstName",
                "last-name": "NewLastName",
                "username": "newusername",
                "bio": "New bio",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Welcome!" in response.data
        assert b"Sign in with your social media" in response.data
        assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_unverified_user_change_personal_info(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.post(
            "/settings/personal-info",
            data={
                "first-name": "NewFirstName",
                "last-name": "NewLastName",
                "username": "newusername",
                "bio": "New bio",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_verified_user_change_personal_info(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/settings/personal-info",
            data={
                "first-name": "NewFirstName",
                "last-name": "NewLastName",
                "username": "newusername",
                "bio": "New bio",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Personal info successfully changed." in response.data

        # TODO Fix this
        updated_user = User.get_by_id(1)
        assert updated_user is not None
        assert updated_user.user_info.first_name == "NewFirstName"  # type: ignore
        assert updated_user.user_info.last_name == "NewLastName"  # type: ignore
        assert updated_user.user_info.username == "newusername"  # type: ignore
        assert updated_user.user_info.bio == "New bio"  # type: ignore


def test_verified_user_change_personal_info_empty_first_name(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/settings/personal-info",
            data={
                "first-name": " ",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"First name cannot be empty." in response.data


def test_verified_user_change_personal_info_empty_last_name(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/settings/personal-info",
            data={
                "last-name": " ",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Last name cannot be empty." in response.data


def test_verified_user_change_personal_info_empty_bio(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/settings/personal-info",
            data={
                "bio": " ",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Bio cannot be empty." in response.data


def test_verified_user_change_personal_info_empty_username(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/settings/personal-info",
            data={
                "username": " ",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Username cannot be empty." in response.data


def test_verified_user_change_personal_info_taken_username(
    client, app, verified_user, username_taken_user, monkeypatch
):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/settings/personal-info",
            data={
                "username": "AngelinaJolie",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Username is taken." in response.data


def test_google_callback(client, app, monkeypatch, verified_user):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        assert response.status_code == 200
        assert b"Search" in response.data


def test_delete_account(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.get(url_for("settings.delete_account"), follow_redirects=True)
        assert response.status_code == 200

        response = client.post(url_for("settings.delete_account"), follow_redirects=True)
        assert response.status_code == 200

        assert b"Globalify" in response.data
        assert b"Your Gateway" in response.data
        assert b"Unlock your business's potential with our extensive network of investors. We're here to help you secure the\nfunding you need to take your business to the next level."

        assert User.get_by_email("johndoe@example.com") is None


def test_settings_company_anonymous_get(client):
    response = client.get("/settings/company", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_company_unverified_get(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/company", follow_redirects=True)
        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_settings_company_verified_get(client, app, new_user_with_company, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/company", follow_redirects=True)
        assert response.status_code == 200
        assert b"Company Information" in response.data
        assert b"Update your company information here." in response.data


def test_verified_user_without_company_get(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/company")
        assert response.status_code == 404


def test_verified_user_change_company_empty_name(client, app, new_user_with_company, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.post(
            url_for("settings.change_company_info"),
            data={
                "company-name": " ",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Company name cannot be empty." in response.data


def test_verified_user_change_company_empty_industry_and_round(client, app, new_user_with_company, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.post(
            url_for("settings.change_company_info"),
            data={
                "industry": None,
                "round": None,
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Please select rounds and industries." in response.data


def test_verified_user_change_company_empty_country(client, app, new_user_with_company, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.post(
            url_for("settings.change_company_info"),
            data={
                "industry": 1,
                "round": 1,
                "country": None,
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Country ID is required." in response.data


def test_verified_user_change_company_valid_data(client, app, new_user_with_company, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "margarita@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(suggestion, "geocode_location", MagicMock(return_value={"coordinates": "20.45,16.5167"}))

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            url_for("settings.change_company_info"),
            data={
                "company-name": "Globalify",
                "description": "Very good company",
                "number_of_employees": 100,
                "industry": 2,
                "round": 2,
                "country": 3,
                "website": "https://www.globalify.com",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Company successfully changed." in response.data

        company = Company.get_by_user_id(1)

        assert company

        assert company.name == "Globalify"
        assert company.description == "Very good company"
        assert company.number_of_employees == 100
        assert company.website_url == "https://www.globalify.com"
        assert company.country_id == 3
        assert company._coordinates == "20.45,16.5167"
        assert company.preferred_round_id == 2
        assert company.industry_id == 2
