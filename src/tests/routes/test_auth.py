from io import BytesIO

import pytest

from src.project.routes.auth import oauth_user
from src.project.utils.status_enum import OauthProvider

from ...project import db
from ...project.models import User, UserInfo, UserOauth, UserPayment, UserRegular
from ...project.utils.errors.auth_error_messages import (
    AUTH_EMAIL_USED,
    OAUTH_MISMATCHED_PROVIDER,
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
def new_user_oauth(app):
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


def test_login_post_method_with_used_oauth(client, new_user_oauth):
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


def test_register_post_method_with_existing_oauth_user(client, new_user_oauth):
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


def test_oauth_user_with_existing_email_different_provider(app, new_user_oauth):
    with app.app_context():
        with pytest.raises(Exception) as e:
            oauth_user(email="janedoe@example.com", oauth_provider=OauthProvider.LINKEDIN)
        assert str(e.value) == OAUTH_MISMATCHED_PROVIDER


def test_oauth_user_with_existing_email_non_oauth_user(app, new_user):
    with app.app_context():
        with pytest.raises(Exception) as e:
            oauth_user(email="johndoe@example.com", oauth_provider=OauthProvider.GOOGLE)
        assert str(e.value) == AUTH_EMAIL_USED


def test_onboarding_anonymous_get(client):
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


def test_onboarding_post_invalid_data(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    data = {
        "first_name": "",
        "last_name": "",
        "username": "",
        "language": "",
        "linkedin": "invalid_linkedin",
        "instagram": "invalid_instagram",
        "twitter": "invalid_twitter",
    }
    response = client.post("/onboarding", data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Profile" in response.data


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
    print(response.text)
    assert response.status_code == 200
    assert b"Dashboard" in response.data
    assert b"Investors" in response.data
    assert b"Firms" in response.data
