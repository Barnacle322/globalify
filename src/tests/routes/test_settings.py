from unittest.mock import MagicMock, patch

import pytest
from flask import url_for
from flask_login import login_user

from src.project import db
from src.project.extensions import oauth
from src.project.models import User, UserInfo, UserPayment
from src.project.models.user import Company, CompanyInvitation, CompanyRole, UserCompany
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
def new_company(app):
    with app.app_context():
        company = Company(name="Test Company")

        company.description = "Test description"
        company.number_of_employees = 10
        company.website_url = "https://www.example.com"
        company.picture_url = "https://www.example.com"
        company.country_id = 1
        company.preferred_round_id = 1
        company.industry_id = 1

        db.session.add(company)
        db.session.commit()

        return company


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

        company = Company(name="Test Company")
        company.description = "Test description"
        company.number_of_employees = 10
        company.website_url = "https://www.example.com"
        company.picture_url = "https://www.example.com"
        company.country_id = 1
        company.preferred_round_id = 1
        company.industry_id = 1
        db.session.add(company)
        db.session.commit()

        user_company = UserCompany(user_id=1, company_id=1)
        user_company.role = CompanyRole.OWNER
        db.session.add(user_company)
        db.session.commit()

        return user


@pytest.fixture()
def new_company_invitation(app):
    with app.app_context():
        company_invitation = CompanyInvitation(email="johndoe@example.com", company_id=1, invited_by=1)

        db.session.add(company_invitation)
        db.session.commit()


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


def test_verified_user_change_personal_info1(client, app, verified_user, monkeypatch):
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

        updated_user = UserInfo.get_by_user_id(1)
        assert updated_user is not None
        assert updated_user.first_name == "NewFirstName"
        assert updated_user.last_name == "NewLastName"
        assert updated_user.username == "newusername"
        assert updated_user.bio == "New bio"


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


def test_verified_user_change_personal_info_add_linkedin_url(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/settings/personal-info",
            data={
                "linkedin": "linkedin.com/in/newLNKDN",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        updated_user = UserInfo.get_by_user_id(1)
        assert updated_user.linkedin_url == "https://linkedin.com/in/newLNKDN"  # type: ignore


def test_verified_user_change_personal_info_add_twitter_url(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/settings/personal-info",
            data={
                "twitter": "twitter.com/newTWTR",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        updated_user = UserInfo.get_by_user_id(1)
        assert updated_user.twitter_url == "https://twitter.com/newTWTR"  # type: ignore


def test_verified_user_change_personal_info_add_instagram_url(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/settings/personal-info",
            data={
                "instagram": "instagram.com/newINSTGRM",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

        updated_user = UserInfo.get_by_user_id(1)
        assert updated_user.instagram_url == "https://instagram.com/newINSTGRM"  # type: ignore


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


def test_settings_company_anonymous_get(client, new_company):
    response = client.get("/settings/company/1", follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_settings_company_unverified_get(client, app, unverified_user, new_company, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/company/1", follow_redirects=True)
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

        response = client.get("/settings/company/1", follow_redirects=True)

        assert response.status_code == 200
        assert b"Company Information" in response.data
        assert b"Update your company information here." in response.data


# ?
def test_verified_user_without_company_get(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/company/1")
        assert b"Company+not+found" in response.data


# Ломается из-за POST метода в функции company_info_view()
# Иначе работает нормально
def test_verified_user_change_company_empty_name(client, app, new_user_with_company, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.post(
            url_for("settings.change_company_info", company_id=1),
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
            url_for("settings.change_company_info", company_id=1),
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
            url_for("settings.change_company_info", company_id=1),
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
            url_for("settings.change_company_info", company_id=1),
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

        company = Company.get_by_id(1)

        assert company

        assert company.name == "Globalify"
        assert company.description == "Very good company"
        assert company.number_of_employees == 100
        assert company.website_url == "https://www.globalify.com"
        assert company.country_id == 3
        assert company._coordinates == "20.45,16.5167"
        assert company.preferred_round_id == 2
        assert company.industry_id == 2


def test_verified_user_change_company_add_social_links(client, app, new_user_with_company, monkeypatch):
    with app.test_request_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "margarita@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(suggestion, "geocode_location", MagicMock(return_value={"coordinates": "20.45,16.5167"}))

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            url_for("settings.change_company_info", company_id=1),
            data={
                "round": 1,
                "industry": 1,
                "country": 1,
                "linkedin": "https://linkedin.com/in/janedoe",
                "instagram": "https://instagram.com/janedoe",
                "twitter": "https://twitter.com/janedoe",
            },
            follow_redirects=True,
        )

        assert response.status_code == 200

        company = Company.get_by_id(1)
        print(company)
        assert company
        assert company.linkedin_url == "https://linkedin.com/in/janedoe"
        assert company.instagram_url == "https://instagram.com/janedoe"
        assert company.twitter_url == "https://twitter.com/janedoe"


def test_get_company_list_view(client, app, new_user_with_company):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/settings/companies", follow_redirects=True)

        assert response.status_code == 200
        assert b"Hmm, it look like you aren't a part of any company." not in response.data
        assert b"Test Company" in response.data
        assert b"Test description" in response.data


def test_create_company_view(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(suggestion, "geocode_location", MagicMock(return_value={"coordinates": "20.45,16.5167"}))

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.get("/settings/company/create", follow_redirects=True)

        assert response.status_code == 200
        assert b"Fill in the details of your company to get started." in response.data
        assert b"Kyrgyzstan" in response.data
        assert b"Series A" in response.data
        assert b"FinTech" in response.data
        assert b"Create" in response.data


def test_create_company(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(suggestion, "geocode_location", MagicMock(return_value={"coordinates": "20.45,16.5167"}))

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            ("/settings/company/create"),
            data={
                "company_name": "Super company",
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
        assert b"Super company" in response.data
        assert b"Very good company" in response.data

        company = Company.get_by_id(1)

        assert company
        assert company.name == "Super company"
        assert company.description == "Very good company"
        assert company.number_of_employees == 100
        assert company.website_url == "https://www.globalify.com"
        assert company.country_id == 3
        assert company._coordinates == "20.45,16.5167"
        assert company.preferred_round_id == 2
        assert company.industry_id == 2


# problem in form_data = request.get_json()
# works when form_data = request.form
# also not working with send_event() function
def test_invite_user(client, app, new_user_with_company, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "margarita@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(suggestion, "geocode_location", MagicMock(return_value={"coordinates": "20.45,16.5167"}))

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            url_for("settings.invite_user", company_id=1),
            data={"email": "johndoe@example.com", "role": "admin", "invitation_message": "wassap free 300$"},
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"User invited" in response.data

        company_invitations = CompanyInvitation.get_by_company_id_and_email(1, "johndoe@example.com")
        assert company_invitations
        assert company_invitations.role == CompanyRole.ADMIN


def test_accept_invitation(client, app, verified_user, new_company, new_company_invitation, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(suggestion, "geocode_location", MagicMock(return_value={"coordinates": "20.45,16.5167"}))

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            url_for("settings.accept_invitation", company_id=1),
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"No companies" not in response.data
        assert b"Test Company" in response.data
        assert b"Test description" in response.data

        user = User.get_by_id(1)
        assert user

        user_company_members = UserCompany.get_members(1)
        assert user in user_company_members[0]


def test_decline_invitation(client, app, verified_user, new_company, new_company_invitation, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(suggestion, "geocode_location", MagicMock(return_value={"coordinates": "20.45,16.5167"}))

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            url_for("settings.decline_invitation", company_id=1),
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"No companies" in response.data
        assert b"Get started by creating a company, or ask to get invited into one" in response.data

        user = User.get_by_id(1)
        assert user

        user_company_members = UserCompany.get_members(1)
        assert not user_company_members


# error in member_id_list = [user_company.user_id for user_company in company_members] - user_id
# work with                  user_company.User.id
def test_get_company_members(client, app, new_user_with_company, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "margarita@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(suggestion, "geocode_location", MagicMock(return_value={"coordinates": "20.45,16.5167"}))

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.get(
            url_for("settings.get_company_members", company_id=1),
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"John" in response.data


def test_get_company_roles(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(suggestion, "geocode_location", MagicMock(return_value={"coordinates": "20.45,16.5167"}))

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.get(
            url_for("settings.get_company_roles"),
            follow_redirects=True,
        )

        assert response.status_code == 200
        assert b"owner" in response.data
        assert b"admin" in response.data
        assert b"team" in response.data

# problem in form_data = request.get_json()
# works when form_data = request.form
def test_change_company_role(client, app, new_user_with_company, verified_user, monkeypatch):
    with app.app_context():
        user_company = UserCompany(user_id=2, company_id=1, role=CompanyRole.TEAM)
        db.session.add(user_company)
        db.session.commit()

        user_company = UserCompany.get_by_user_id(2)
        assert user_company[0].role == CompanyRole.TEAM

        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "margarita@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(suggestion, "geocode_location", MagicMock(return_value={"coordinates": "20.45,16.5167"}))

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            url_for("settings.change_company_role", user_id=2),
            data={"role": "admin", "company_id": 1},
            follow_redirects=True,
        )

        assert response.status_code == 200
        user_company = UserCompany.get_by_user_id(2)
        assert user_company[0].role == CompanyRole.ADMIN
