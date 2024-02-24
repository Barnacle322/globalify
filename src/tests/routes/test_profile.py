import pytest

from src.project import db
from src.project.models import UserInfo, UserPayment, UserRegular
from src.project.models.user import Company


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
            first_name="Margarita",
            last_name="Kusher",
            username="Margi",
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


def test_user_profile_authenticated_get(client, new_user_with_company):
    client.post("/login", data=dict(email="margarita@example.com", password="password"), follow_redirects=True)
    response = client.get("/profile/user/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"User Profile" in response.data
    assert b"Company Profile" in response.data
    assert b"Margarita Kusher" in response.data


def test_user_profile_anonymous_get(client):
    response = client.get("/profile/user/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_company_profile_authenticated_get(client, new_user_with_company):
    client.post("/login", data=dict(email="margarita@example.com", password="password"), follow_redirects=True)
    response = client.get("/profile/company/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"User Profile" in response.data
    assert b"Company Profile" in response.data
    assert b"Test Company" in response.data
    assert b"Test description" in response.data


def test_company_profile_anonymous_get(client):
    response = client.get("/profile/company/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_company_profile_authenticated_without_company_get(client, new_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/profile/company/1", follow_redirects=True)
    assert response.status_code == 404
