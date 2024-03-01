from unittest.mock import MagicMock

import pytest
from flask import url_for

from src.project import db
from src.project.extensions import oauth
from src.project.models.helpers import Industry, Round
from src.project.models.investor import InvestmentFirm, Investor, NotableInvestment
from src.project.models.user import Notification, User, UserInfo, UserPayment, WaitlistCharge
from src.project.utils.enums import NotificationDestination, NotificationLayout, OauthProvider
from src.project.utils.errors.error_messages import AUTH_FIELDS_INCOMPLETE


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Globalify" in response.data
    assert b"Your Gateway to Investors" in response.data
    assert b"Tailored experience for specific regions" in response.data
    assert b"Unlock your business's potential with our extensive network of investors." in response.data
    assert b"Finding investors with ease" in response.data


def test_about(client):
    response = client.get("/about")
    assert response.status_code == 200
    assert b"mission and vision" in response.data
    assert b"Our Passion" in response.data
    assert b"The what, the how, the who" in response.data
    assert b"Our team" in response.data
    assert b"info@globalify.xyz" in response.data
    assert b"Use Globalify - Fund Your Startup" in response.data


def test_waitlist_email(client):
    response = client.post(
        "/waitlist-email", json=dict(email="johndoe@example.com"), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert b"Email added." in response.data


def test_waitlist_email_empty(client):
    response = client.post("/waitlist-email", json=dict(email=""), headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    assert b"Please enter an email." in response.data


def test_waitlist_email_invalid(client):
    response = client.post(
        "/waitlist-email", json=dict(email="invalid_email"), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert b"Please enter a valid email." in response.data


def test_waitlist_email_duplicate(client):
    client.post("/waitlist-email", json=dict(email="johndoe@example.com"), headers={"Content-Type": "application/json"})
    response = client.post(
        "/waitlist-email", json=dict(email="johndoe@example.com"), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert b"Email is already in the system." in response.data


def test_waitlist_cancel(client):
    response = client.get("/waitlist/cancel")
    assert response.status_code == 200
    assert b"Payment canceled" in response.data
    assert b"You have not been charged." in response.data
    assert b"Go to dashboard" in response.data


def test_waitlist_success(client):
    response = client.get("/waitlist/success")
    assert response.status_code == 200
    assert b"Thank you!" in response.data
    assert b"Thank you for your purchase!" in response.data
    assert b"Home" in response.data


def test_download_refused(client):
    response = client.get("/download/random_key")
    assert response.status_code == 200
    assert b"Huh! It looks like you may have already downloaded our list of investors." in response.data
    assert b"Please check your downloads folder." in response.data


def test_download_already_downloaded(client, app):
    with app.app_context():
        waitlist_charge = WaitlistCharge(
            stripe_customer_id="stripe_id",
            charge_id="charge_id",
            customer_email="cus@example.com",
            customer_name="John Doe",
            random_key="12345",
            downloaded=True,
        )
        db.session.add(waitlist_charge)
        db.session.commit()
        response = client.get("/download/12345")
        assert response.status_code == 200
        assert b"Huh! It looks like you may have already downloaded our list of investors." in response.data
        assert b"Please check your downloads folder." in response.data


def test_download_success(client, app):
    with app.app_context():
        waitlist_charge = WaitlistCharge(
            stripe_customer_id="stripe_id",
            charge_id="charge_id",
            customer_email="cus@example.com",
            customer_name="John Doe",
            random_key="12345",
            downloaded=False,
        )
        db.session.add(waitlist_charge)
        db.session.commit()
        response = client.get("/download/12345")
        assert response.status_code == 200
        assert (
            b"Download a curated list featuring lead investors perfectly matched for your startup in different industries."
            in response.data
        )
        assert b"Please note, that you can only download this file" in response.data


def test_download_post_wrong_key(client, app):
    with app.app_context():
        waitlist_charge = WaitlistCharge(
            stripe_customer_id="stripe_id",
            charge_id="charge_id",
            customer_email="cus@example.com",
            customer_name="John Doe",
            random_key="12345",
            downloaded=False,
        )
        db.session.add(waitlist_charge)
        db.session.commit()
    response = client.post("/download", data={"key": "54321"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Globalify" in response.data
    assert b"Your Gateway to Investors" in response.data
    assert b"Tailored experience for specific regions" in response.data
    assert b"Unlock your business's potential with our extensive network of investors." in response.data
    assert b"Finding investors with ease" in response.data


def test_download_post_already_downloaded(client, app):
    with app.app_context():
        waitlist_charge = WaitlistCharge(
            stripe_customer_id="stripe_id",
            charge_id="charge_id",
            customer_email="cus@example.com",
            customer_name="John Doe",
            random_key="12345",
            downloaded=True,
        )
        db.session.add(waitlist_charge)
        db.session.commit()
    response = client.post("/download", data={"key": "12345"}, follow_redirects=True)
    assert response.status_code == 200
    assert b"Globalify" in response.data
    assert b"Your Gateway to Investors" in response.data
    assert b"Tailored experience for specific regions" in response.data
    assert b"Unlock your business's potential with our extensive network of investors." in response.data
    assert b"Finding investors with ease" in response.data


def test_download_post_success(client, app):
    with app.app_context():
        waitlist_charge = WaitlistCharge(
            stripe_customer_id="stripe_id",
            charge_id="charge_id",
            customer_email="cus@example.com",
            customer_name="John Doe",
            random_key="12345",
            downloaded=False,
        )
        db.session.add(waitlist_charge)
        db.session.commit()
    response = client.post("/download", data={"random_key": "12345"}, follow_redirects=True)
    content_disposition = response.headers.get("Content-Disposition", "")
    assert "attachment" in content_disposition
    with app.app_context():
        updated_waitlist_charge = WaitlistCharge.get_by_random_key("12345")
        assert updated_waitlist_charge
        assert updated_waitlist_charge.downloaded


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
def verified_user_wtih_waitlist_charge(app):
    with app.app_context():
        user = User(
            oauth_provider=OauthProvider.GOOGLE,
            email="johny@example.com",
            is_verified=True,
        )
        db.session.add(user)
        db.session.commit()

        user_info = UserInfo(
            first_name="John",
            last_name="Doe",
            username="johny",
            is_complete=True,
            user=user,
        )
        user_payment = UserPayment(
            customer_id="cus_123",
            user=user,
        )
        db.session.add_all([user_info, user_payment])
        db.session.commit()

        wailist_charge = WaitlistCharge(
            stripe_customer_id="stripe_id",
            charge_id="charge_id",
            customer_email="johny@example.com",
            customer_name="John Doe",
            random_key="12345",
            downloaded=False,
        )
        db.session.add(wailist_charge)
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
def investor(app):
    with app.app_context():
        investor = Investor(
            first_name="Julie",
            last_name="Doe",
            about="Julie is a founder and CEO at Qwerty LLC. She is a great investor.",
            firm_name="Qwerty LLC",
            position="CEO",
            rounds=[Round.get_by_id(1), Round.get_by_id(2)],
            industries=[Industry.get_by_id(1), Industry.get_by_id(2)],
            min_investment=1_000_000,
            max_investment=15_000_000,
        )
        db.session.add(investor)
        db.session.commit()


@pytest.fixture()
def populate_investor(app):
    with app.app_context():
        Investor.populate()


@pytest.fixture()
def populate_notable_investment(app):
    with app.app_context():
        NotableInvestment.populate()


@pytest.fixture()
def investment_firm(app):
    with app.app_context():
        investment_firm = InvestmentFirm(
            name="Qwerty LLC",
            about="Qwerty LLC is a great investment firm.",
            website="https://qwerty.com",
            email="qwerty@example.com",
            rounds=[Round.get_by_id(1), Round.get_by_id(2)],
            industries=[Industry.get_by_id(1), Industry.get_by_id(2)],
            min_investment=10_000_000,
            max_investment=50_000_000,
        )
        db.session.add(investment_firm)
        db.session.commit()


@pytest.fixture()
def populate_investment_firm(app):
    with app.app_context():
        InvestmentFirm.populate()


def test_dashboard_anonymous_get(client):
    response = client.get("/search", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_dashboard_unverified_get(client, unverified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="johndoe@example.com"), follow_redirects=True)

        response = client.get("/search", follow_redirects=True)

        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_dashboard_verified_get(client, verified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="johndoe@example.com"), follow_redirects=True)

        response = client.get("/search")
        assert response.status_code == 200
        assert b"View more" in response.data
        assert b"Sign up for our Early Bird tier to get full access to the database of investors!" in response.data


def test_dashboard_firm_anonymous_get(client):
    response = client.get("/investment-firm/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_dashboard_firm_unverified_get(client, unverified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="johndoe@example.com"), follow_redirects=True)

        response = client.get("/investment-firm/1", follow_redirects=True)

        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_dashboard_firm_not_found_verified_get(client, verified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="johndoe@example.com"), follow_redirects=True)

        response = client.get("/investment-firm/1", follow_redirects=True)
        assert response.status_code == 200
        assert b"View more" in response.data
        assert b"Sign up for our Early Bird tier to get full access to the database of investors!" in response.data


def test_error_handler_404(client):
    response = client.get("/non-existing-page", follow_redirects=True)
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_investor_anonymous_get(client):
    response = client.get("/investor/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_investor_unverified_get(client, unverified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="johndoe@example.com"), follow_redirects=True)

        response = client.get("/investor/1", follow_redirects=True)

        assert response.status_code == 200
        assert b"Email Verification" in response.data
        assert (
            b"A verification email has been sent to you! Click the link or input a code to verify your email address."
            in response.data
        )
        assert b"Verify" in response.data


def test_investor_verified_get(client, verified_user, investor, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="johndoe@example.com"), follow_redirects=True)
        response = client.get("/investor/1", follow_redirects=True)
        assert response.status_code == 200
        assert b"Julie" in response.data
        assert b"Qwerty LLC" in response.data
        assert b"Julie is a founder and CEO at Qwerty LLC. She is a great investor." in response.data
        assert b"Industries" in response.data
        assert b"Rounds" in response.data


def test_investor_not_found(client, verified_user, investor, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="johndoe@example.com"), follow_redirects=True)
        response = client.get("/investor/99999999", follow_redirects=True)
        assert response.status_code == 200
        assert b"View more" in response.data
        assert b"Sign up for our Early Bird tier to get full access to the database of investors!" in response.data


def test_notification_anonymous_edit(client):
    response = client.get("/notification/edit/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome!" in response.data
    assert b"Sign in with your social media" in response.data
    assert b"Oops! Looks like you aren&#39;t logged in" in response.data


def test_edit_not_found_notification(client, verified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="johndoe@example.com"), follow_redirects=True)
        response = client.get("/notification/edit/99999999", follow_redirects=True)
        assert response.status_code == 200
        assert b"View more" in response.data
        assert b"Sign up for our Early Bird tier to get full access to the database of investors!" in response.data


def test_edit_notification_mismatch_user(client, verified_user, verified_user_wtih_waitlist_charge, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="johndoe@example.com"), follow_redirects=True)

        user = User.get_by_id(2)

        assert user is not None

        notification = Notification(
            user=user,
            json_data=NotificationLayout(title="Error!", msg=AUTH_FIELDS_INCOMPLETE).get_json(),
            destination=NotificationDestination.ONBOARDING,
        )
        db.session.add(notification)
        db.session.commit()

        response = client.get("/notification/edit/1", follow_redirects=True)
        assert response.status_code == 200
        assert b"View more" in response.data
        assert b"Sign up for our Early Bird tier to get full access to the database of investors!" in response.data


def test_success_edit_notification(client, verified_user, app, monkeypatch):
    with app.app_context():
        mock_authorize = MagicMock(
            return_value={"userinfo": {"email": "johndoe@example.com", "given_name": "Test", "family_name": "User"}}
        )
        monkeypatch.setattr(oauth.google, "authorize_access_token", mock_authorize)

        response = client.get(url_for("auth.google_callback"), follow_redirects=True)

        client.post("/login", data=dict(email="johndoe@example.com"), follow_redirects=True)

        user = User.get_by_id(1)

        assert user is not None

        notification = Notification(
            user=user,
            json_data=NotificationLayout(title="Error!", msg=AUTH_FIELDS_INCOMPLETE).get_json(),
            destination=NotificationDestination.ONBOARDING,
        )
        db.session.add(notification)
        db.session.commit()

        response = client.get("/notification/edit/1", follow_redirects=True)

        updated_notification = Notification.get_by_user_id(1)

        assert updated_notification is not None
        assert updated_notification.is_read
        assert response.status_code == 200
        assert b'[\n  {\n    "status": "success"\n  },\n  200\n]\n' in response.data


# TODO
# def test_firm_get(client, new_user, investment_firm):
#     client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
#     response = client.get("/investment-firm/1", follow_redirects=True)
#     assert response.status_code == 200
#     assert b"Qwerty LLC" in response.data
#     assert b"Qwerty LLC is a great investment firm." in response.data
#     assert b"Industries" in response.data
#     assert b"Rounds" in response.data

# TODO
# def test_firm_not_found(client, new_user, investment_firm):
#     client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
#     response = client.get("/investment-firm/99999999", follow_redirects=True)
#     assert response.status_code == 200
#     assert b"Investors" in response.data
#     assert b"Firms" in response.data
#     assert b"Only show firms with selected rounds" in response.data
#     assert b"Only show firms with selected industries" in response.data


def test_pricing(client):
    response = client.get("/pricing")
    assert response.status_code == 200
    print(response.data)
    assert b"Pricing" in response.data
    assert b"Flexible Pricing Options for Advanced Search Solutions" in response.data
    assert b"Perfect for small startups" in response.data
    assert b"Subscribe" in response.data


def test_terms_of_service(client):
    response = client.get("/terms-of-service")
    assert response.status_code == 200
    assert b"Terms of Service" in response.data


def test_privacy_policy(client):
    response = client.get("/privacy-policy")
    assert response.status_code == 200
    assert b"Privacy Policy" in response.data
    assert b"SUMMARY OF KEY POINTS" in response.data
    assert b"Personal information you disclose to us" in response.data
