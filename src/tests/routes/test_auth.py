from urllib.parse import quote_plus

import pytest

from src.project.utils.status_enum import OauthProvider

from ...project import db
from ...project.models import User, UserInfo, UserOauth, UserPayment, UserRegular
from ...project.utils.errors.auth_error_messages import (
    AUTH_EMAIL_NOT_FOUND,
    AUTH_EMAIL_USED,
    AUTH_FIELDS_INCOMPLETE,
    AUTH_INCORRECT_PASSWORD,
    AUTH_INVALID_EMAIL,
    AUTH_MISMATCHED_PASSWORDS,
    AUTH_OAUTH_USED,
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


@pytest.fixture()
def new_user_oauth(app):
    with app.app_context():
        user = UserOauth(email="janedoe@example.com", oauth_provider=OauthProvider.GOOGLE)
        db.session.add(user)
        db.session.commit()


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
    response = client.post("/login", data={"email": "", "password": ""})
    assert response.status_code == 302
    assert quote_plus(AUTH_FIELDS_INCOMPLETE) in response.location


def test_login_post_method_with_used_oauth(client, new_user_oauth):
    response = client.post("/login", data={"email": "janedoe@example.com", "password": "password"})
    assert response.status_code == 302
    assert quote_plus(AUTH_OAUTH_USED) in response.location


def test_login_post_method_with_invalid_email(client):
    response = client.post("/login", data={"email": "nonexisting@email.com", "password": "password"})
    assert response.status_code == 302
    assert quote_plus(AUTH_EMAIL_NOT_FOUND) in response.location


def test_login_post_method_with_invalid_password(client, new_user):
    response = client.post("/login", data={"email": "johndoe@example.com", "password": "incorrect_password"})
    assert response.status_code == 302
    assert quote_plus(AUTH_INCORRECT_PASSWORD) in response.location


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
    response = client.post("/register", data={"email": "", "password": "", "confirm_password": ""})
    assert response.status_code == 302
    assert quote_plus(AUTH_FIELDS_INCOMPLETE) in response.location


def test_register_post_method_with_invalid_email(client):
    response = client.post(
        "/register", data={"email": "invalid_email", "password": "password123", "confirm_password": "password123"}
    )
    assert response.status_code == 302
    assert quote_plus(AUTH_INVALID_EMAIL) in response.location


def test_register_post_method_with_mismatched_passwords(client):
    response = client.post(
        "/register", data={"email": "janedoe@example.com", "password": "password123", "confirm_password": "password321"}
    )
    assert response.status_code == 302
    assert quote_plus(AUTH_MISMATCHED_PASSWORDS) in response.location


def test_register_post_method_with_existing_oauth_user(client, new_user_oauth):
    response = client.post(
        "/register",
        data={"email": "janedoe@example.com", "password": "password123", "confirm_password": "password123"},
    )
    assert response.status_code == 302
    assert quote_plus(AUTH_OAUTH_USED) in response.location


def test_register_post_method_with_existing_user(client, new_user):
    response = client.post(
        "/register", data={"email": "johndoe@example.com", "password": "password", "confirm_password": "password"}
    )
    assert response.status_code == 302
    assert quote_plus(AUTH_EMAIL_USED) in response.location
