import datetime
from unittest.mock import MagicMock, patch

import pytest
from flask import url_for
from flask_login import login_user
from freezegun import freeze_time

from src.project import db
from src.project.extensions import oauth
from src.project.models import Company, User, UserInfo, UserPayment
from src.project.models.user import EmailVerification
from src.project.routes.auth import oauth_user
from src.project.utils.enums import OauthProvider
from src.project.utils.errors.error_messages import (
    OAUTH_MISMATCHED_PROVIDER,
    OAUTH_NO_EMAIL,
    OAUTH_NO_USER_INFO,
)
from src.project.utils.google_helpers import google_pubsub


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


@pytest.fixture()
def unverified_incomplete_user(app):
    with app.app_context():
        user = User(
            oauth_provider=OauthProvider.GOOGLE,
            email="janedoe@example.com",
        )
        db.session.add(user)
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


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data


def test_unverified_user_login(client, app, unverified_user, monkeypatch):
    with app.app_context():
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


def test_verified_user_login(client, app, verified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        assert response.status_code == 200

        assert b"Pick For Me" in response.data
        assert b"To get better recommendations, complete your profile."


def test_oauth_user_with_existing_email_different_provider(app, verified_user):
    with app.app_context():
        with pytest.raises(Exception) as e:
            oauth_user(email="johndoe@example.com", oauth_provider=OauthProvider.LINKEDIN)
        assert str(e.value) == OAUTH_MISMATCHED_PROVIDER


def test_onboarding_anonymous_get(client):
    response = client.get("/onboarding", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_onboarding_authenticated_user(client, app, unverified_incomplete_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"))

        response = client.get("/onboarding")
        assert response.status_code == 200
        assert b"We just need some more info" in response.data


def test_onboarding_post_valid_data(client, app, unverified_incomplete_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "janedoe@example.com", "given_name": "John", "family_name": "Doe"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)
        monkeypatch.setattr(target=google_pubsub, name="send_event", value=MagicMock())

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/onboarding",
            data={
                "first_name": "John",
                "last_name": "Doe",
                "username": "johndoe",
                "company_name": "Globalify",
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

        user = User.get_by_id(1)

        assert user.user_info.is_complete  # type: ignore
        assert user.user_info.first_name == "John"  # type: ignore
        assert user.user_info.last_name == "Doe"  # type: ignore
        assert user.user_info.username == "johndoe"  # type: ignore

        company = Company.get_by_id(1)
        assert company is not None
        assert company.name == "Globalify"


def test_onboarding_incomplete(client, app, unverified_incomplete_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "janedoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="janedoe@example.com"), follow_redirects=True)
        response = client.post(
            "/onboarding",
            data={
                "first_name": "",
                "last_name": "",
                "username": "",
                "language": "English",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Error!" in response.data
        assert b"Please fill out all fields." in response.data


def test_nickname_taken(client, app, unverified_incomplete_user, unverified_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "janedoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.post(
            "/onboarding",
            data={
                "first_name": "user",
                "last_name": "new",
                "username": "johndoe",
                "company_name": "Globalify",
            },
            follow_redirects=True,
        )
        assert response.status_code == 200
        assert b"Error!" in response.data
        assert b"Username is already in use." in response.data
        assert UserInfo.is_taken("johndoe")


def test_logout_endpoint(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)
        login_user(user)

        response = client.get("/logout", follow_redirects=True)
        assert response.status_code == 200
        assert b"Globalify" in response.data
        assert b"Your Gateway to Investors" in response.data
        assert (
            b"Unlock your business's potential with our extensive network of investors and partners." in response.data
        )


def test_username_anonymous_get(client):
    response = client.get("/username/johndoe", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_username_verified_get(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)

        login_user(user)
        response = client.get("/username/johndoe", follow_redirects=True)
        assert response.status_code == 200
        assert b"is_taken" in response.data


def test_verify_email_anonymous_get(client):
    response = client.get("/verify-email?uuid=invalid_token", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_verify_email_incomplete_user_get(client, app, unverified_incomplete_user, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        response = client.get("/verify-email?uuid=invalid_token", follow_redirects=True)
        assert response.status_code == 200
        assert b"We just need some more info" in response.data


def test_verify_email_invalid_token(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)

        login_user(user)

        response = client.get("/verify-email?uuid=invalid_token", follow_redirects=True)
        assert response.status_code == 200
        assert b"Invalid code" in response.data
        assert b"The code you have put in is invalid" in response.data


def test_verify_email_expired_token(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        with freeze_time("2024-01-01 12:00:00"):
            user = User.get_by_id(1)

            login_user(user)

            expired_verification = EmailVerification(user_id=1)
            expired_verification.created_at = datetime.datetime.now()
            db.session.add(expired_verification)
            db.session.commit()

        with freeze_time("2024-01-01 13:00:00"):
            response = client.get(f"/verify-email?uuid={expired_verification.token}", follow_redirects=True)
            assert b"Error" in response.data
            assert b"Email verification code has expired." in response.data
            assert response.status_code == 200


def test_verify_email_already_verified(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)

        login_user(user)

        verified_verification = EmailVerification(user_id=1)
        db.session.add(verified_verification)
        db.session.commit()

        response = client.get(f"/verify-email?uuid={verified_verification.token}", follow_redirects=True)
        assert response.status_code == 200
        assert b"Pick For Me" in response.data
        assert b"To get better recommendations, complete your profile."


def test_verify_email_already_used(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)

        login_user(user)

        verified_verification = EmailVerification(user_id=1)
        verified_verification.is_used = True
        db.session.add(verified_verification)
        db.session.commit()

        response = client.get(f"/verify-email?uuid={verified_verification.token}", follow_redirects=True)
        assert response.status_code == 200
        assert b"Pick For Me" in response.data
        assert b"To get better recommendations, complete your profile."


def test_verify_email_mismatch_user(client, app, unverified_user, unverified_incomplete_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)

        login_user(user)
        verification_token = EmailVerification(user_id=2)
        db.session.add(verification_token)
        db.session.commit()

        response = client.get(f"/verify-email?uuid={verification_token.token}", follow_redirects=True)

        assert response.status_code == 200
        assert b"Hmm, we couldn&#39;t find your account. Please reach out to our support team!" in response.data


def test_resend_verification_email_user_not_found(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)

        login_user(user)
        response = client.get("/resend-verification/999", follow_redirects=True)

        assert response.status_code == 200
        assert b"Hmm, we couldn&#39;t find your account. Please reach out to our support team!" in response.data


def test_resend_verification_email_already_verified(client, app, verified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)

        login_user(user)
        response = client.get("/resend-verification/1", follow_redirects=True)

        assert response.status_code == 200
        assert b"Pick For Me" in response.data
        assert b"To get better recommendations, complete your profile."


def test_resend_verification_very_quick(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)

        login_user(user)

        monkeypatch.setattr(target=google_pubsub, name="send_event", value=MagicMock())

        client.get("/resend-verification/1", follow_redirects=True)

        response = client.get("/resend-verification/1", follow_redirects=True)

        assert response.status_code == 200
        assert b"Hey! Slow down.." in response.data
        assert b"You can only request a new code every minute." in response.data


def test_resend_verification_email_success(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)

        login_user(user)

        monkeypatch.setattr(target=google_pubsub, name="send_event", value=MagicMock())

        response = client.get("/resend-verification/1", follow_redirects=True)

        assert response.status_code == 200
        assert b"Verification code sent!" in response.data
        assert (
            b"Please check your email for the new verification code. It may take a few minutes to arrive."
            in response.data
        )


def test_verify_email_success(client, app, unverified_user, monkeypatch):
    with app.test_request_context():
        user = User.get_by_id(1)

        login_user(user)

        valid_verification = EmailVerification(user_id=1)
        db.session.add(valid_verification)
        db.session.commit()

        response = client.get(f"/verify-email?uuid={valid_verification.token}", follow_redirects=True)

        assert response.status_code == 200
        assert b"Pick For Me" in response.data
        assert b"To get better recommendations, complete your profile."

        updated_user = User.get_by_id(1)
        assert updated_user is not None
        assert updated_user.is_verified

        updated_verification = EmailVerification.get_by_token(valid_verification.token)
        assert updated_verification is not None
        assert updated_verification.is_used


@pytest.fixture()
def linkedin_user_oauth(app):
    with app.app_context():
        user = User(
            oauth_provider=OauthProvider.LINKEDIN,
            email="linkedinuseroauth@example.com",
            is_verified=True,
        )
        db.session.add(user)
        user_info = UserInfo(
            first_name="user",
            last_name="oauth",
            username="usernameoauth",
            is_complete=True,
            user=user,
        )
        db.session.add(user_info)
        db.session.commit()
        return user


def test_linkedin_callback(client, app, linkedin_user_oauth):
    with app.app_context():
        with (
            patch("src.project.routes.auth.oauth.linkedin") as mock_oauth,
            patch("src.project.routes.auth.api_call") as mock_api_call,
        ):
            mock_oauth.authorize_access_token.return_value = {"access_token": "mock_token"}
            mock_api_call.return_value = {
                "elements": [{"handle~": {"emailAddress": "linkedinuseroauth@example.com"}}],
                "localizedFirstName": "user",
                "localizedLastName": "oauth",
            }

            response = client.get(url_for("auth.linkedin_callback"), follow_redirects=True)
            assert response.status_code == 200
            assert b"Pick For Me" in response.data
            assert b"To get better recommendations, complete your profile."
            assert b"Search" in response.data


def test_linkedin_callback_authorization_failure(client, app):
    with app.app_context():
        with (
            patch("src.project.routes.auth.oauth.linkedin") as mock_oauth,
            patch("src.project.routes.auth.api_call") as mock_api_call,
        ):
            mock_oauth.authorize_access_token.return_value = {"access_token": "mock_token"}
            mock_api_call.return_value = {
                "elements": [{"handle~": {"emailAddress": None}}],
                "localizedFirstName": "user",
                "localizedLastName": "oauth",
            }

            response = client.get(url_for("auth.linkedin_callback"), follow_redirects=True)

            assert response.status_code == 200
            assert OAUTH_NO_EMAIL in response.text


def test_linkedin_with_existing_google_oauth_user(client, app, verified_user):
    with app.app_context():
        with (
            patch("src.project.routes.auth.oauth.linkedin") as mock_oauth,
            patch("src.project.routes.auth.api_call") as mock_api_call,
        ):
            mock_oauth.authorize_access_token.return_value = {"access_token": "mock_token"}
            mock_api_call.return_value = {
                "elements": [{"handle~": {"emailAddress": "johndoe@example.com"}}],
                "localizedFirstName": "user",
                "localizedLastName": "oauth",
            }

            response = client.get(url_for("auth.linkedin_callback"), follow_redirects=True)
            assert response.status_code == 200
            assert OAUTH_MISMATCHED_PROVIDER in response.text


def test_google_callback(client, app, monkeypatch, verified_user):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        assert response.status_code == 200
        assert b"Pick For Me" in response.data
        assert b"To get better recommendations, complete your profile."
        assert b"Profile" in response.data


def test_google_callback_user_info_failure(client, app, monkeypatch, verified_user):
    with app.app_context():
        mock_authorize = MagicMock(return_value={"userinfo": None})
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        assert response.status_code == 200
        assert OAUTH_NO_USER_INFO in response.text


def test_google_callback_user_info_no_email(client, app, monkeypatch, verified_user):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": None, "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        assert response.status_code == 200
        assert OAUTH_NO_EMAIL in response.text


def test_google_callback_email_linkedin(client, app, monkeypatch, linkedin_user_oauth):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={
                "userinfo": {"email": "linkedinuseroauth@example.com", "given_name": "Test", "family_name": "User"}
            }
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        assert response.status_code == 200
        assert OAUTH_MISMATCHED_PROVIDER in response.text
