from unittest.mock import MagicMock

import pytest
from flask import url_for

from src.project.models.user import User
from src.project.utils.status_enum import OauthProvider

from ...project import db
from ...project.extensions import oauth
from ...project.models import UserInfo, UserOauth, UserPayment, UserRegular


@pytest.fixture()
def new_user(app):
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
def new_user2(app):
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


def test_settings_anonymous_get(client):
    response = client.get("/settings/general", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data


def test_settings_authenticated_get(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/settings/general")
    assert response.status_code == 200
    assert b"Personal Information" in response.data
    assert b"Use a permanent address where you can receive mail." in response.data


def test_settings_security_authenticated_get(client, new_user):
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


def test_settings_plan_authenticated_get(client, new_user):
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


# TODO: fix this test
def test_settings_billing_authenticated_get(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/settings/billing")
    assert response.status_code == 200
    assert b"Manage billing" in response.data
    assert b"Manage your billing details with Stripe." in response.data


def test_settings_billing_anonymous_get(client):
    response = client.get("/settings/plan", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data


def test_settings_change_personal_info(client, new_user, app):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "first-name": "NewFirstName",
            "last-name": "NewLastName",
            "email": "newemail@example.com",
            "username": "newusername",
            "bio": "New bio",
            "language": "en",
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


def test_change_personal_info_empty_first_name(client, new_user):
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


def test_change_personal_info_empty_last_name(client, new_user):
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


def test_change_personal_info_empty_email(client, new_user):
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


def test_change_personal_info_invalid_email(client, new_user):
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


# TODO: fix this test
def test_change_personal_info_oauth_user_email(client, new_user_oauth):
    client.post("/login", data=dict(email="janedoe@example.com", password="password"), follow_redirects=True)

    response = client.post(
        "/settings/personal-info",
        data={
            "email": "agahan@gmail.com",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Cannot change email for oauth users." in response.data


def test_change_personal_info_empty_bio(client, new_user):
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


def test_change_personal_info_empty_username(client, new_user):
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


def test_change_personal_info_taken_username(client, new_user, new_user2):
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


def test_change_personal_info_empty_language(client, new_user):
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


def test_change_personal_info_invalid_language(client, new_user):
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


def test_change_password(client, new_user):
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


def test_change_password_invalid_password(client, new_user):
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


def test_change_password_mismatch_password(client, new_user):
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


def test_change_password_empty_password(client, new_user):
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


def test_change_password_empty_confirm_password(client, new_user):
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


# TODO: Fix this test
def test_change_password_oauth_user(client, new_user_oauth):
    client.post("/login", data={"email": "janedoe@example.com", "password": "password"}, follow_redirects=True)

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
    assert b"Cannot change password for oauth users." in response.data


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
