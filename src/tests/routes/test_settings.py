import pytest

from src.project.models.user import User
from src.project.utils.status_enum import OauthProvider

from ...project import db
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
def new_user_oauth(app):
    with app.app_context():
        user = UserOauth(email="janedoe@example.com", oauth_provider=OauthProvider.GOOGLE)
        db.session.add(user)
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

    with app.app_context():
        updated_user = User.query.filter_by(email="johndoe@example.com").first()
        assert updated_user is not None
        assert updated_user.user_info[0].first_name == "NewFirstName"
        assert updated_user.user_info[0].last_name == "NewLastName"
        assert updated_user.user_info[0].username == "newusername"
        assert updated_user.user_info[0].bio == "New bio"
        assert updated_user.user_info[0].language == "en"
