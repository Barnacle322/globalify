import pytest

from src.project import db
from src.project.models.helpers import Industry, Round
from src.project.models.investor import InvestmentFirm, Investor, NotableInvestment
from src.project.models.user import UserInfo, UserRegular, WaitlistCharge


def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Globalify is" in response.data
    assert b"Tailored experience for specific regions" in response.data
    assert b"Frequently asked questions" in response.data
    assert b"From the blog" in response.data
    assert b"Use Globalify - Fund Your Startup" in response.data


def test_waitlist(client):
    response = client.get("/waitlist")
    assert response.status_code == 200
    assert b"Limited time offer!" in response.data
    assert b"Frequently asked questions" in response.data
    assert b"Use Globalify - Fund Your Startup" in response.data


def test_about(client):
    response = client.get("/about")
    assert response.status_code == 200
    assert b"mission and vision" in response.data
    assert b"Our Passion" in response.data
    assert b"Our platform" in response.data
    assert b"The what, the how, the who" in response.data
    assert b"The team" in response.data
    assert b"info@globalify.xyz" in response.data
    assert b"Use Globalify - Fund Your Startup" in response.data


def test_waitlist_apply(client):
    response = client.get("/waitlist/apply")
    assert response.status_code == 200
    assert b"Join Globalify!" in response.data
    assert b"Email" in response.data
    assert b"First name" in response.data
    assert b"Last name" in response.data
    assert b"Proceed" in response.data


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
    assert b"Go to home" in response.data


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
    assert b"Globalify is" in response.data
    assert b"Tailored experience for specific regions" in response.data
    assert b"Frequently asked questions" in response.data
    assert b"From the blog" in response.data
    assert b"Use Globalify - Fund Your Startup" in response.data


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
    assert b"Globalify is" in response.data
    assert b"Tailored experience for specific regions" in response.data
    assert b"Frequently asked questions" in response.data
    assert b"From the blog" in response.data
    assert b"Use Globalify - Fund Your Startup" in response.data


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
        user = UserRegular(
            email="johndoe@example.com",
            password="password",
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
        db.session.add_all(
            [
                user_info,
            ]
        )
        db.session.commit()
        return user


@pytest.fixture()
def unverified_user(app):
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
    response = client.get("/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data


def test_dashboard_authenticated_unverified_get(client, unverified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Email Verification Required" in response.data
    assert (
        b"If the link in the message is not working, you can manually enter the code you received in the message."
        in response.data
    )
    assert b"Resend Verification Email" in response.data


def test_dashboard_authenticated_get(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Find Ideal Investor" in response.data
    assert b"Only show investors with selected rounds" in response.data
    assert b"Only show investors with selected industries" in response.data


def test_dashboard_query_search(client, verified_user, investor):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard?search=Julie")

    assert response.status_code == 200
    assert b"Julie" in response.data
    assert b"Doe" in response.data
    assert b"Qwerty LLC" in response.data


# TODO: What is this?
# def test_dashboard_query_page(client, new_user, populate_notable_investment, populate_investor):
#     client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
#     response = client.get("/dashboard?page=2")
#     assert response.status_code == 200
#     assert b'current="page"\n                        >2</a' in response.data


def test_dashboard_query_industry(client, verified_user, populate_notable_investment, populate_investor):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard?industry=AI")
    assert response.status_code == 200
    assert b"AI" in response.data


def test_dashboard_query_round(client, verified_user, populate_notable_investment, populate_investor):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard?round=Seed")
    assert response.status_code == 200
    assert b"Seed" in response.data


def test_dashboard_query_industry_and_round(client, verified_user, populate_notable_investment, populate_investor):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard?industry=AI&round=Seed")
    assert response.status_code == 200
    assert b"AI" in response.data
    assert b"Seed" in response.data


def test_dashboard_firms_anonymous_get(client):
    response = client.get("/dashboard/investment-firms", follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back!" in response.data
    assert b"Sign in" in response.data


def test_dashboard_firms_authenticated_get(client, verified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard/investment-firms")
    assert response.status_code == 200
    assert b"Investors" in response.data
    assert b"Firms" in response.data
    assert b"Only show firms with selected rounds" in response.data
    assert b"Only show firms with selected industries" in response.data


def test_dashboard_firms_authenticated_unverified_get(client, unverified_user):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard/investment-firms")
    assert response.status_code == 200
    assert b"Email Verification Required" in response.data
    assert (
        b"If the link in the message is not working, you can manually enter the code you received in the message."
        in response.data
    )
    assert b"Resend Verification Email" in response.data


def test_dashboard_firms_query_search(client, verified_user, investment_firm):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard/investment-firms?search=Qwerty")
    assert response.status_code == 200
    assert b"Qwerty LLC" in response.data
    assert b"Qwerty LLC is a great investment firm." in response.data


def test_dashboard_firms_query_page(client, verified_user, populate_investment_firm):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard/investment-firms?page=2")
    assert response.status_code == 200
    assert b'current="page"\n                        >2</a' in response.data


def test_dashboard_firms_query_industry(client, verified_user, populate_investment_firm):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard/investment-firms?industry=AI")
    assert response.status_code == 200
    assert b"AI" in response.data


def test_dashboard_firms_query_round(client, verified_user, populate_investment_firm):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard/investment-firms?round=Seed")
    assert response.status_code == 200
    assert b"Seed" in response.data


def test_dashboard_firms_query_industry_and_round(client, verified_user, populate_investment_firm):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/dashboard/investment-firms?industry=AI&round=Seed")
    assert response.status_code == 200
    assert b"AI" in response.data
    assert b"Seed" in response.data


def test_error_handler_404(client):
    response = client.get("/non-existing-page", follow_redirects=True)
    assert response.status_code == 404
    assert b"Page not found" in response.data


def test_investor_get(client, verified_user, investor):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/investor/1", follow_redirects=True)
    assert response.status_code == 200
    assert b"Julie" in response.data
    assert b"Qwerty LLC" in response.data
    assert b"Julie is a founder and CEO at Qwerty LLC. She is a great investor." in response.data
    assert b"Industries" in response.data
    assert b"Rounds" in response.data


def test_investor_not_found(client, verified_user, investor):
    client.post("/login", data=dict(email="johndoe@example.com", password="password"), follow_redirects=True)
    response = client.get("/investor/99999999", follow_redirects=True)
    assert response.status_code == 200
    assert b"Find Ideal Investor" in response.data
    assert b"Only show investors with selected rounds" in response.data
    assert b"Only show investors with selected industries" in response.data


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
    assert b"Simple pricing for everyone." in response.data
    assert b"Perfect for small start-ups that are still ideating." in response.data
    assert b"Works best for start-ups in their pre-seed and seed rounds." in response.data


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
