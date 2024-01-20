from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from flask import url_for

from src.project import db
from src.project.extensions import oauth
from src.project.models import User, UserInfo, UserOauth, UserPayment, UserRegular
from src.project.routes.auth import oauth_user
from src.project.utils.errors.auth_error_messages import (
    AUTH_EMAIL_USED,
    OAUTH_MISMATCHED_PROVIDER,
    OAUTH_NO_EMAIL,
    OAUTH_NO_USER_INFO,
)
from src.project.utils.status_enum import OauthProvider


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
            "pfp": (BytesIO(b"my test file contents"), "test.jpg"),
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
        "pfp": (BytesIO(b"my test file contents"), "test.jpg"),
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
            "pfp": (BytesIO(b"my test file contents"), "test.jpg"),
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
            "pfp": (BytesIO(b"my test file contents"), "test.jpg"),
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


def test_company_form_authenticated_post(client, user_with_complete_user_info, app):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.post(
        "/company-form",
        data={
            "company_name": "Test Company",
            "about": "Test description",
            "country": 1,
            "round": 1,
            "industry": 1,
            "website": "https://www.example.com",
            "pfp": (BytesIO(b"my test file contents"), "test.jpg"),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert b"Investors" in response.data
    assert b"Firms" in response.data


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
