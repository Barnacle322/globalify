from unittest.mock import MagicMock, patch

import pytest
from flask import url_for

from src.project import db
from src.project.extensions import oauth
from src.project.models import UserInfo, UserOauth, UserPayment, UserRegular
from src.project.models.user import Company, User
from src.project.utils.status_enum import OauthProvider


@pytest.fixture()
def verified_user(app):
    with app.app_context():
        user = UserRegular(
            email="johndoe@example.com",
            is_verified=True,
            password="password",
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
        user = UserRegular(
            email="angelina@example.com",
            is_verified=True,
            password="password",
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
def new_user_oauth(app):
    with app.app_context():
        user = UserOauth(email="janedoe@example.com", oauth_provider=OauthProvider.GOOGLE, is_verified=True)
        db.session.add(user)
        db.session.commit()
        user_info = UserInfo(
            first_name="Jane",
            last_name="Doe",
            username="janedoe",
            is_complete=True,
            user=user,
        )
        db.session.add(user_info)
        db.session.commit()
        return user


@pytest.fixture()
def new_user_with_company(app):
    with app.app_context():
        user = UserRegular(
            email="margarita@example.com",
            is_verified=True,
            password="password",
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
        company = Company(
            name="Test Company",
            description="Test description",
            number_of_employees=10,
            website="https://www.example.com",
            country_id=1,
            preferred_round_id=1,
            industry_id=1,
            user=user,
        )
        db.session.add(company)
        db.session.commit()
        return user


def test_settings_anonymous_get(client):
    response = client.get("/settings/general", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_authenticated_unverified_get(client, unverified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/settings/general")
    assert response.status_code == 200
    assert b"Email Verification Required" in response.data
    assert (
        b"If the link in the message is not working, you can manually enter the code you received in the message."
        in response.data
    )
    assert b"Resend Verification Email" in response.data


def test_settings_authenticated_get(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/settings/general")
    assert response.status_code == 200
    assert b"Personal Information" in response.data
    assert b"Use a permanent address where you can receive mail." in response.data


def test_settings_security_authenticated_unverified_get(client, unverified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/settings/security")
    assert response.status_code == 200
    assert b"Email Verification Required" in response.data
    assert (
        b"If the link in the message is not working, you can manually enter the code you received in the message."
        in response.data
    )
    assert b"Resend Verification Email" in response.data


def test_settings_security_authenticated_get(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/settings/security")
    assert response.status_code == 200
    assert b"Change password" in response.data
    assert b"Update your password associated with your account." in response.data


def test_settings_security_anonymous_get(client):
    response = client.get("/settings/security", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_plan_authenticated_unverified_get(client, unverified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/settings/plan")
    assert response.status_code == 200
    assert b"Email Verification Required" in response.data
    assert (
        b"If the link in the message is not working, you can manually enter the code you received in the message."
        in response.data
    )
    assert b"Resend Verification Email" in response.data


def test_settings_plan_authenticated_get(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/settings/plan")
    assert response.status_code == 200
    assert b"Your subscription" in response.data
    assert b"This is your current subscription. You can update your plan any time." in response.data


def test_settings_plan_anonymous_get(client):
    response = client.get("/settings/plan", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_billing_authenticated_unverified_get(client, unverified_user):
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

        client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
        response = client.get("/settings/billing", follow_redirects=True)

    assert response.status_code == 200
    assert b"Email Verification Required" in response.data
    assert (
        b"If the link in the message is not working, you can manually enter the code you received in the message."
        in response.data
    )
    assert b"Resend Verification Email" in response.data


def test_settings_billing_authenticated_get(client, verified_user):
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

        client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
        response = client.get("/settings/billing", follow_redirects=True)

    assert response.status_code == 200
    assert b"Manage billing" in response.data
    assert b"Manage your billing details with" in response.data
    assert b"See your invoice history here." in response.data


def test_settings_billing_anonymous_get(client):
    response = client.get("/settings/plan", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_change_personal_info(client, verified_user, app):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "first-name": "NewFirstName",
            "last-name": "NewLastName",
            "email": "newemail@example.com",
            "username": "newusername",
            "bio": "New bio",
            "language": "English",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Personal info successfully changed." in response.data

    with app.app_context():
        updated_user = User.query.filter_by(email="newemail@example.com").first()
        assert updated_user is not None
        assert updated_user.user_info[0].first_name == "NewFirstName"
        assert updated_user.user_info[0].last_name == "NewLastName"
        assert updated_user.email == "newemail@example.com"
        assert updated_user.user_info[0].username == "newusername"
        assert updated_user.user_info[0].bio == "New bio"
        assert updated_user.user_info[0].language == "English"


def test_change_personal_info_empty_first_name(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "first-name": " ",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"First name cannot be empty." in response.data


def test_change_personal_info_empty_last_name(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "last-name": " ",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Last name cannot be empty." in response.data


def test_change_personal_info_empty_email(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "email": " ",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Email cannot be empty." in response.data


def test_change_personal_info_invalid_email(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "email": "johndoe@examplecom",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Have and account? Click " in response.data


def test_change_personal_info_oauth_user_email(client, new_user_oauth, app, monkeypatch):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "janedoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="janedoe@example.com", password="password"), follow_redirects=True)

        settings_response = client.post(
            "/settings/personal-info",
            data={
                "email": "agahan@gmail.com",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert settings_response.status_code == 200
        assert b"Cannot change email for oauth users." in settings_response.data


def test_change_personal_info_empty_bio(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "bio": " ",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Bio cannot be empty." in response.data


def test_change_personal_info_empty_username(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "username": " ",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Username cannot be empty." in response.data


def test_change_personal_info_taken_username(client, verified_user, username_taken_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "username": "AngelinaJolie",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Username is taken." in response.data


def test_change_personal_info_empty_language(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "language": " ",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Language cannot be empty." in response.data


def test_change_personal_info_invalid_language(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "language": "Kyrgyz",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Invalid language." in response.data


def test_change_password(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/change-password",
        data={
            "current-password": "password",
            "new-password": "new-password",
            "confirm-password": "new-password",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Password successfully changed." in response.data


def test_change_password_invalid_password(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/change-password",
        data={
            "current-password": "invalid-password",
            "new-password": "new-password",
            "confirm-password": "new-password",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Incorrect password." in response.data


def test_change_password_mismatch_password(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/change-password",
        data={
            "current-password": "password",
            "new-password": "new-password",
            "confirm-password": "mismatch-password",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Passwords do not match." in response.data


def test_change_password_empty_password(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/change-password",
        data={
            "current-password": "",
            "new-password": "new-password",
            "confirm-password": "new-password",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Please fill out all fields." in response.data


def test_change_password_empty_confirm_password(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/change-password",
        data={
            "current-password": "password",
            "new-password": "new-password",
            "confirm-password": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Please fill out all fields." in response.data


def test_change_password_oauth_user(client, new_user_oauth, app, monkeypatch):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "janedoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data={"email": "janedoe@example.com", "password": "password"}, follow_redirects=True)

        settings_response = client.post(
            "/settings/change-password",
            data={
                "current-password": "password",
                "new-password": "new-password",
                "confirm-password": "new-password",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert settings_response.status_code == 200
        assert b"Cannot change password for oauth users." in settings_response.data


def test_google_callback(app, client, monkeypatch, new_user_oauth):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "janedoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        assert response.status_code == 200
        assert b"Search" in response.data


def test_delete_account(client, verified_user, app):
    with app.test_request_context():
        client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

        response = client.get(url_for("settings.delete_account"), follow_redirects=True)
        assert response.status_code == 200

        response = client.post(url_for("settings.delete_account"), follow_redirects=True)
        assert response.status_code == 200

        assert b"Launching Soon" in response.data
        assert b"100 Early Access spots!" in response.data

        assert User.get_by_email("johndoe@example.com") is None


def test_settings_company_anonymous_get(client):
    response = client.get("/settings/company", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_company_authenticated_get(client, new_user_with_company):
    client.post("/login", data=dict(email="margarita@example.com", password="password"), follow_redirects=True)
    response = client.get("/settings/company")
    assert response.status_code == 200
    assert b"Company Information" in response.data
    assert b"Update your company information here." in response.data


def test_settings_company_authenticated_without_company_get(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/settings/company")
    assert response.status_code == 404


def test_change_company_empty_name(client, new_user_with_company, app):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        client.post("/login", data=dict(email="margarita@example.com", password="password"), follow_redirects=True)
        response = client.post(
            url_for("settings.change_company_info"),
            data={
                "company-name": " ",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"Company name cannot be empty." in response.data


def test_change_company_empty_industry_and_round(client, new_user_with_company, app):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        client.post("/login", data=dict(email="margarita@example.com", password="password"), follow_redirects=True)
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


def test_change_company_empty_country(client, new_user_with_company, app):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        client.post("/login", data=dict(email="margarita@example.com", password="password"), follow_redirects=True)
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


def test_change_company_valid_data(client, new_user_with_company, app):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        client.post("/login", data=dict(email="margarita@example.com", password="password"), follow_redirects=True)
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
        assert company.website == "https://www.globalify.com"
        assert company.country_id == 3
        assert company.preferred_round_id == 2
        assert company.industry_id == 2
