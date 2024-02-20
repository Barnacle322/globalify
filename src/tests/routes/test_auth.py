import datetime
from unittest.mock import MagicMock, patch

import pytest
from flask import url_for

from src.project import db
from src.project.extensions import oauth
from src.project.models import User, UserInfo, UserOauth, UserPayment, UserRegular
from src.project.models.user import EmailVerification
from src.project.routes.auth import oauth_user
from src.project.utils.enums import OauthProvider
from src.project.utils.errors.error_messages import (
    AUTH_EMAIL_USED,
    OAUTH_MISMATCHED_PROVIDER,
    OAUTH_NO_EMAIL,
    OAUTH_NO_USER_INFO,
)


@pytest.fixture()
def new_user(app):
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
def google_user_oauth(app):
    with app.app_context():
        user = UserOauth(email="janedoe@example.com", oauth_provider=OauthProvider.GOOGLE)
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture()
def verified_user(app):
    with app.app_context():
        user = UserRegular(email="johndoe@example.com", password="password", is_verified=True)
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
        return user


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data


def test_login(client, new_user):
    response = client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Profile" in response.data


def test_login_post_method_with_empty_fields(client):
    response = client.post("/login", data={"email": "", "password": ""}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Please fill out all fields." in response.data


def test_login_post_method_with_used_oauth(client, google_user_oauth):
    response = client.post(
        "/login", data={"email": "janedoe@example.com", "password": "password"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Please sign in with your OAuth provider." in response.data


def test_login_post_method_with_invalid_email(client):
    response = client.post(
        "/login", data={"email": "nonexisting@email.com", "password": "password"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"User associated with this email does not exist." in response.data


def test_login_post_method_with_invalid_password(client, new_user):
    response = client.post(
        "/login", data={"email": "johndoe@example.com", "password": "incorrect_password"}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"The password is incorrect" in response.data


def test_register_page(client):
    response = client.get("/register")
    assert response.status_code == 200
    assert b"Have and account?" in response.data
    assert b"Sign up" in response.data


def test_register(client, app):
    response = client.post(
        "/register",
        data=dict(email="janedoe@example.com", password="password", confirm_password="password"),
        follow_redirects=True,
    )
    assert response.status_code == 200
    with app.app_context():
        user = User.get_by_email("janedoe@example.com")
        assert user


def test_register_post_method_with_empty_fields(client):
    response = client.post(
        "/register", data={"email": "", "password": "", "confirm_password": ""}, follow_redirects=True
    )
    assert response.status_code == 200
    assert b"Please fill out all fields." in response.data


def test_register_post_method_with_invalid_email(client):
    response = client.post(
        "/register",
        data={"email": "invalid_email", "password": "password123", "confirm_password": "password123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Please enter a valid email." in response.data


def test_register_post_method_with_mismatched_passwords(client):
    response = client.post(
        "/register",
        data={"email": "janedoe@example.com", "password": "password123", "confirm_password": "password321"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Passwords do not match." in response.data


def test_register_post_method_with_existing_oauth_user(client, google_user_oauth):
    response = client.post(
        "/register",
        data={"email": "janedoe@example.com", "password": "password123", "confirm_password": "password123"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Please sign in with your OAuth provider." in response.data


def test_register_post_method_with_existing_user(client, new_user):
    response = client.post(
        "/register",
        data={"email": "johndoe@example.com", "password": "password", "confirm_password": "password"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Email is already in use." in response.data


def test_oauth_user_with_new_email(app):
    with app.app_context():
        user = oauth_user(email="testoauth@example.com", oauth_provider=OauthProvider.GOOGLE)
        assert user
        assert user.email == "testoauth@example.com"
        assert isinstance(user, UserOauth)


def test_oauth_user_with_existing_email_different_provider(app, google_user_oauth):
    with app.app_context():
        with pytest.raises(Exception) as e:
            oauth_user(email="janedoe@example.com", oauth_provider=OauthProvider.LINKEDIN)
        assert str(e.value) == OAUTH_MISMATCHED_PROVIDER


def test_oauth_user_with_existing_email_non_oauth_user(app, new_user):
    with app.app_context():
        with pytest.raises(Exception) as e:
            oauth_user(email="johndoe@example.com", oauth_provider=OauthProvider.GOOGLE)
        assert str(e.value) == AUTH_EMAIL_USED


def test_onboarding_anonymous_get(client, app):
    response = client.get("/onboarding", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data


def test_onboarding_authenticated_user(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/onboarding", follow_redirects=True)
    assert response.status_code == 200
    assert b"Profile" in response.data
    assert b"This information will be displayed publicly so be careful what you share." in response.data


def test_onboarding_post_valid_data(client, new_user, app):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.post(
        "/onboarding",
        data={
            "first_name": "John",
            "last_name": "Doe",
            "username": "johndoe",
            "language": "English",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Company profile" in response.data
    with app.app_context():
        user_info = UserInfo.get_by_user_id(1)
        assert user_info.is_complete  # type: ignore


def test_onboarding_post_invalid_url_data(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "username": "johndoe",
        "language": "English",
        "linkedin": "invalid_linkedin",
        "instagram": "invalid_instagram",
        "twitter": "invalid_twitter",
    }
    response = client.post("/onboarding", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Profile" in response.data
    assert "Invalid" in str(response.request)
    assert "url" in str(response.request)


@pytest.fixture()
def user_with_nickname(app):
    with app.app_context():
        user = UserRegular(
            email="user1@example.com",
            password="password",
        )
        db.session.add(user)
        user_info = UserInfo(
            first_name="user",
            last_name="old",
            username="takenusername",
            user=user,
        )
        db.session.add(user_info)
        db.session.commit()
        return user


@pytest.fixture()
def user_without_nickname(app):
    with app.app_context():
        user = UserRegular(
            email="user2@example.com",
            password="password",
        )
        db.session.add(user)
        user_info = UserInfo(
            first_name="user",
            last_name="new",
            user=user,
        )
        db.session.add(user_info)
        db.session.commit()
        return user


def test_onboarding_incomplete(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
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
    assert "Please+fill+out+all+fields." in str(response.request)


def test_nickname_taken(client, user_with_nickname, user_without_nickname, app):
    client.post("/login", data=dict(email="user2@example.com", password="password"), follow_redirects=True)
    response = client.post(
        "/onboarding",
        data={
            "first_name": "user",
            "last_name": "new",
            "username": "takenusername",
            "language": "English",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Username+is+already+in+use." in str(response.request)
    with app.app_context():
        assert UserInfo.is_taken("takenusername")


def test_logout_endpoint(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"About Us" in response.data
    assert b"Blog" in response.data


def test_username_anonymous_get(client):
    response = client.get("/username/johndoe", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data


def test_username_authenticated_get(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/username/johndoe", follow_redirects=True)
    assert response.status_code == 200
    assert b"is_taken" in response.data


def test_company_form_anonymous_get(client):
    response = client.get("/company-form", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data


def test_company_form_authenticated_get(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/company-form", follow_redirects=True)
    assert response.status_code == 200
    assert b"Company profile" in response.data
    assert b"This information will be displayed publicly so be careful what you share." in response.data


@pytest.fixture()
def user_with_complete_user_info(app):
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
        db.session.add_all(
            [
                user_info,
            ]
        )
        db.session.commit()
        return user


def test_company_form_authenticated_post(client, app, user_with_complete_user_info, monkeypatch):
    with app.test_request_context():
        client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
        mock_email = MagicMock(
            return_value={
                "sent": True,
            }
        )
        monkeypatch.setattr("src.project.utils.sendgrid_email.send_email", mock_email)
        response = client.post(
            "/company-form",
            data={
                "company_name": "Test Company",
                "about": "About Test Company",
                "country": "1",
                "round": "1",
                "industry": "1",
                "website": "http://testcompany.com",
            },
            follow_redirects=True,
        )
        assert mock_email.return_value is not None
        assert response.status_code == 200
        assert b"Verify Email" in response.data
        assert b"Resend Verification Email" in response.data


def test_verify_email_invalid_token(client):
    response = client.get("/verify-email/?uuid=invalid_token")
    assert b"Invalid Verification Token" in response.data
    assert response.status_code == 200


def test_verify_email_expired_token(client, app, user_with_complete_user_info):
    with app.app_context():
        expired_verification = EmailVerification(
            user_id=1, created_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=20)
        )
        db.session.add(expired_verification)
        db.session.commit()

        response = client.get(f"/verify-email/?uuid={expired_verification.token}")
        assert b"Verification Token Expired" in response.data
        assert response.status_code == 200


def test_verify_email_already_verified(client, app, verified_user):
    with app.app_context():
        verified_verification = EmailVerification(user_id=1)
        db.session.add(verified_verification)
        db.session.commit()

        response = client.get(f"/verify-email/?uuid={verified_verification.token}")

        assert b"Already Verified" in response.data
        assert b"Great news! Your account is already verified." in response.data
        assert response.status_code == 200


def test_verify_email_already_used(client, app, verified_user):
    with app.app_context():
        client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
        verified_verification = EmailVerification(user_id=1)
        verified_verification.is_used = True
        db.session.add(verified_verification)
        db.session.commit()

        response = client.get(f"/verify-email/?uuid={verified_verification.token}")
        assert b"Already Used" in response.data
        assert b"Oops! It seems this code has already been used." in response.data
        assert response.status_code == 200


def test_resend_verification_email_user_not_found(client, user_with_complete_user_info):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/resend-verification/999")
    assert response.status_code == 404


def test_resend_verification_email_already_verified(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/resend-verification/1")
    assert b"Already Verified" in response.data
    assert b"Great news! Your account is already verified." in response.data
    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert b"Find Ideal Investor" in response.data


def test_resend_verification_email_success(client, user_with_complete_user_info, app):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
        user = UserRegular.get_by_id(1)
        assert user is not None

        verification_token = "valid_token"
        new_verification = EmailVerification(user_id=user.id, token=verification_token)
        db.session.add(new_verification)
        db.session.commit()
        assert new_verification is not None

        response = client.get("/resend-verification/1")
        assert response.status_code == 302
        assert response.location == "/search/investors"

        updated_verification = EmailVerification.get_by_token(verification_token)
        assert updated_verification is not None
        assert updated_verification.is_expired

        updated_user = UserRegular.get_by_id(1)
        assert updated_user is not None
        assert updated_user.is_verified is False


def test_verify_email_success(client, app, user_with_complete_user_info):
    with app.app_context():
        valid_verification = EmailVerification(user_id=1)
        db.session.add(valid_verification)
        db.session.commit()

        response = client.get(f"/verify-email/?uuid={valid_verification.token}")
        assert b"Email Verified" in response.data
        assert response.status_code == 200

        updated_user = UserRegular.get_by_id(1)
        assert updated_user is not None
        assert updated_user.is_verified is True

        updated_verification = EmailVerification.get_by_token(valid_verification.token)
        assert updated_verification is not None
        assert updated_verification.is_used


@pytest.fixture()
def linkedin_user_oauth(app):
    with app.app_context():
        user = UserOauth(email="linkedinuseroauth@example.com", oauth_provider=OauthProvider.LINKEDIN, is_verified=True)
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


def test_linkedin_callback(client, linkedin_user_oauth, app):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        with patch("src.project.routes.auth.oauth.linkedin") as mock_oauth, patch(
            "src.project.routes.auth.api_call"
        ) as mock_api_call:
            mock_oauth.authorize_access_token.return_value = {"access_token": "mock_token"}
            mock_api_call.return_value = {
                "elements": [{"handle~": {"emailAddress": "linkedinuseroauth@example.com"}}],
                "localizedFirstName": "user",
                "localizedLastName": "oauth",
            }

            response = client.get(url_for("auth.linkedin_callback"), follow_redirects=True)

            assert response.status_code == 200
            assert b"Search" in response.data


def test_linkedin_callback_authorization_failure(client, app):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        with patch("src.project.routes.auth.oauth.linkedin") as mock_oauth, patch(
            "src.project.routes.auth.api_call"
        ) as mock_api_call:
            mock_oauth.authorize_access_token.return_value = {"access_token": "mock_token"}
            mock_api_call.return_value = {
                "elements": [{"handle~": {"emailAddress": None}}],
                "localizedFirstName": "user",
                "localizedLastName": "oauth",
            }

            response = client.get(url_for("auth.linkedin_callback"), follow_redirects=True)

            assert response.status_code == 200
            assert OAUTH_NO_EMAIL in response.text


def test_linkedin_with_existing_google_oauth_user(client, google_user_oauth, app):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        with patch("src.project.routes.auth.oauth.linkedin") as mock_oauth, patch(
            "src.project.routes.auth.api_call"
        ) as mock_api_call:
            mock_oauth.authorize_access_token.return_value = {"access_token": "mock_token"}
            mock_api_call.return_value = {
                "elements": [{"handle~": {"emailAddress": "janedoe@example.com"}}],
                "localizedFirstName": "user",
                "localizedLastName": "oauth",
            }

            response = client.get(url_for("auth.linkedin_callback"), follow_redirects=True)
            assert response.status_code == 200
            assert OAUTH_MISMATCHED_PROVIDER in response.text


def test_google_callback(app, client, monkeypatch, google_user_oauth):
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
        assert b"Profile" in response.data


def test_google_callback_user_info_failure(app, client, monkeypatch, google_user_oauth):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        mock_authorize = MagicMock(return_value={"userinfo": None})
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        assert response.status_code == 200
        assert OAUTH_NO_USER_INFO in response.text


def test_google_callback_user_info_no_email(app, client, monkeypatch, google_user_oauth):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": None, "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        assert response.status_code == 200
        assert OAUTH_NO_EMAIL in response.text


def test_google_callback_email_linkedin(app, client, monkeypatch, linkedin_user_oauth):
    app.config["SERVER_NAME"] = "localhost"
    app.config["APPLICATION_ROOT"] = ""
    app.config["PREFERRED_URL_SCHEME"] = "http"
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
