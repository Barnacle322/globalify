import pytest

from ...project import db
from ...project.models import User, UserInfo, UserPayment, UserRegular


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


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data


def test_login(client, new_user):
    response = client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    assert response.status_code == 200
    assert b"Profile" in response.data


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
