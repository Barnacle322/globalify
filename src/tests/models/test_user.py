import datetime

import pytest
from freezegun import freeze_time

from src.project.models.user import ClaimRequest, CompanyInvitation

from ...project import db
from ...project.models import (
    Company,
    Industry,
    Investor,
    NotableInvestment,
    Round,
    User,
    UserCompany,
    UserInfo,
    UserPayment,
)
from ...project.utils.enums import CompanyRole, OauthProvider, Tier


@pytest.fixture()
def new_user_oauth(app):
    with app.app_context():
        user = User(email="janedoe@example.com", oauth_provider=OauthProvider.GOOGLE)
        db.session.add(user)
        db.session.commit()

        user_info = UserInfo(
            first_name="Jane",
            last_name="Doe",
            username="janedoe",
            user=user,
            linkedin_url="https://linkedin.com/in/janedoe",
            twitter_url="https://twitter.com/janedoe",
            instagram_url="https://instagram.com/janedoe",
            bio="I'm a cool person",
        )
        user_payment = UserPayment(
            customer_id="cus_123",
            subscription_id="sub_123",
            is_active=True,
            tier=Tier.FREE,
            user=user,
        )
        user_payment.created_epoch = 1609462861
        user_payment.expires_at_epoch = 1612141261

        db.session.add_all([user_info, user_payment])
        db.session.commit()


@pytest.fixture()
def new_company(app):
    with app.app_context():
        company = Company(name="Globalify")

        company.description = "A very cool company"
        company.number_of_employees = 3
        company.website_url = "https://globalify.xyz"
        company.picture_url = "https://www.example.com"
        company.country_id = 235
        company.preferred_round_id = 1
        company.industry_id = 1
        db.session.add(company)
        db.session.commit()


@pytest.fixture()
def new_user_company(app):
    with app.app_context():
        user_company = UserCompany(user_id=1, company_id=1)

        db.session.add(user_company)
        db.session.commit()


# CompanyInvitation имеет company_id и company
@pytest.fixture()
def new_company_invitation(app):
    with app.app_context():
        company_invitation = CompanyInvitation(
            email="johndoe@example.com",
            company_id=1,
            invited_by=1,
        )

        db.session.add(company_invitation)
        db.session.commit()


@pytest.fixture()
def new_claim_request(app):
    with app.app_context():
        notable_investment = NotableInvestment(name="Notable Investment")
        db.session.add(notable_investment)
        db.session.commit()

        investor = Investor(
            first_name="Jane",
            last_name="Doe",
            firm_name="BerkshireHathaway",
            about="Passionate investor",
            position="Investment Analyst",
            website="https://berkshire.com",
            linkedin="linkedin_acc",
            twitter="twitter_acc",
            email="jane@example.com",
            slug="jane-doe",
            phone_number="+999123123123",
            n_investments=20,
            n_exits=50,
            min_investment=100000,
            max_investment=50000000,
            bias=15,
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment],
        )

        db.session.add(investor)
        db.session.commit()

        claim_request = ClaimRequest(user_id=1, investor_id=1, email="jane@example.com", status_info="approved")
        db.session.add(claim_request)
        db.session.commit()


def test_is_company_invitation_expired(app, new_company, new_user_oauth, new_company_invitation):
    with app.app_context():
        company_invitation = db.session.scalar(db.select(CompanyInvitation).where(CompanyInvitation.id == 1))
        assert company_invitation
        assert not company_invitation.is_expired()

        company_invitation.created_at = datetime.datetime.now() - datetime.timedelta(days=8)
        assert company_invitation.is_expired()


def test_get_company_invination_by_id(app, new_user_oauth, new_company, new_company_invitation):
    with app.app_context():
        company_invitation = CompanyInvitation.get_by_id(1)

        assert company_invitation
        assert company_invitation.email == "johndoe@example.com"


def test_get_company_invination_by_email(app, new_user_oauth, new_company, new_company_invitation):
    with app.app_context():
        company_invitation = CompanyInvitation.get_by_email("johndoe@example.com")

        assert company_invitation
        assert company_invitation[0].id == 1


def test_get_company_invination_by_id_and_email(app, new_user_oauth, new_company, new_company_invitation):
    with app.app_context():
        company_invitation = CompanyInvitation.get_by_company_id_and_email(1, "johndoe@example.com")

        assert company_invitation
        assert company_invitation.id == 1


def test_get_company_invination_by_company_id(app, new_user_oauth, new_company, new_company_invitation):
    with app.app_context():
        company_invitation = CompanyInvitation.get_by_company_id(1)

        assert company_invitation
        assert company_invitation[0].email == "johndoe@example.com"


def test_empty_db(app):
    with app.app_context():
        users = User.get_all()
        assert isinstance(users, list)
        assert len(users) == 0

        user = User.get_by_email("johndoe@example.com")
        assert user is None

        user = User.get_by_id(1)
        assert user is None

        company = Company.get_by_id(1)
        assert company is None

        user_company = UserCompany.get_by_user_and_company_id(1, 1)
        assert user_company is None


def test_user_oauth(new_user_oauth, app):
    with app.app_context():
        user = User.get_by_email("janedoe@example.com")
        users = User.get_all()

        assert users and len(users) == 1
        assert user and isinstance(user, User)

        assert user.oauth_provider == OauthProvider.GOOGLE
        assert user.is_verified is False
        assert user.is_admin is False


def test_user_info(new_user_oauth, app):
    with app.app_context():
        user_info = UserInfo.get_by_user_id(1)
        user_infos = UserInfo.get_all()

        assert user_info
        assert user_infos and len(user_infos) == 1

        assert user_info.first_name == "Jane"
        assert user_info.last_name == "Doe"
        assert user_info.username == "janedoe"
        # assert UserInfo.validate_linkedin(user_info) == "https://linkedin.com/in/janedoe"
        assert user_info.linkedin_url == "https://linkedin.com/in/janedoe"
        assert user_info.twitter_url == "https://twitter.com/janedoe"
        assert user_info.instagram_url == "https://instagram.com/janedoe"
        assert user_info.bio == "I'm a cool person"
        assert user_info.picture_url is None

        assert UserInfo.is_taken("janedoe")
        assert not UserInfo.is_taken("johndoe")
        assert user_info.sanitize() == {
            "user_id": 1,
            "username": "janedoe",
            "first_name": "Jane",
            "last_name": "Doe",
            "linkedin": "https://linkedin.com/in/janedoe",
            "instagram": "https://instagram.com/janedoe",
            "twitter": "https://twitter.com/janedoe",
            "bio": "I'm a cool person",
            "pfp": None,
        }


@freeze_time("2021-01-02")
def test_user_payment(new_user_oauth, app):
    with app.app_context():
        user_payment = UserPayment.get_by_customer_id("cus_123")
        assert user_payment
        user_payment = UserPayment.get_by_user_id(1)
        assert user_payment
        assert user_payment.customer_id == "cus_123"
        assert user_payment.subscription_id == "sub_123"
        assert user_payment.created == datetime.datetime(2021, 1, 1, 1, 1, 1)
        assert user_payment.expires_at == datetime.datetime(2021, 2, 1, 1, 1, 1)
        assert user_payment.is_active is True
        assert user_payment.tier == Tier.FREE

        assert user_payment.is_expired() is False
        assert user_payment.sanitize() == {
            "created": datetime.datetime(2021, 1, 1, 1, 1, 1),
            "expires_at": datetime.date(2021, 2, 1),
            "is_active": True,
            "tier": Tier.FREE,
            "subscription_id": "sub_123",
        }


@freeze_time("2021-03-01")
def test_user_payment_expired(new_user_oauth, app):
    with app.app_context():
        user_payment = db.session.scalar(db.select(UserPayment).where(UserPayment.id == 1))
        assert user_payment
        assert user_payment.is_expired() is True


def test_company(new_user_oauth, new_company, app):
    with app.app_context():
        company = Company.get_by_id(1)
        assert company
        company = Company.get_by_id(1)
        assert company
        assert company.id == 1
        assert company.name == "Globalify"
        assert company.description == "A very cool company"
        assert company.number_of_employees == 3
        assert company.website_url == "https://globalify.xyz"
        assert company.country_id == 235
        assert company.preferred_round_id == 1
        assert company.industry_id == 1


def test_user_company(new_user_oauth, new_company, new_user_company, app):
    with app.app_context():
        user = User.get_by_id(1)
        company = Company.get_by_id(1)
        user_company = UserCompany.get_by_user_id(1)

        assert user
        assert company
        assert user_company
        assert user_company[0].user_id == user.id
        assert user_company[0].company_id == company.id
        assert user_company[0].role == CompanyRole.TEAM


# Проблема в функции delete_by_id()
def test_delete_by_id(new_user_oauth, new_company, new_user_company, app):
    with app.app_context():
        user = User.get_by_id(1)
        company = Company.get_by_id(1)
        user_info = UserInfo.get_by_user_id(1)
        user_payment = UserPayment.get_by_user_id(1)
        user_company = db.session.scalar(db.select(UserCompany).where(UserCompany.id == 1))

        assert user
        assert company
        assert company.name == "Globalify"
        assert user_info
        assert user_info.first_name == "Jane"
        assert user_payment
        assert user_payment.is_active
        assert user_company
        assert user_company.user_id == 1

        User.delete_by_id(1)
        assert not user
        assert not company
        assert not user_info
        assert not user_payment
        assert not user_company


def test_get_by_subscription_id(new_user_oauth, app):
    with app.app_context():
        user_payment = UserPayment.get_by_subscription_id("sub_123")
        user = User.get_by_id(1)

        assert user_payment
        assert user_payment.user == user


def test_get_user_company_by_company_id(new_user_oauth, new_company, new_user_company, app):
    with app.app_context():
        user_company = UserCompany.get_by_company_id(1)
        assert user_company
        assert user_company[0].user_id == 1


def test_get_by_user_id_and_company_id(new_user_oauth, new_company, new_user_company, app):
    with app.app_context():
        user = User.get_by_id(1)
        company = Company.get_by_id(1)
        assert user
        assert company

        user_company = UserCompany.get_by_user_and_company_id(1, 1)

        assert user_company
        assert user_company.user_id == user.id
        assert user_company.company_id == company.id


def test_get_by_company_id_and_email(new_user_oauth, new_company, new_user_company, app):
    with app.app_context():
        company = Company.get_by_id(1)
        assert company

        user_company = UserCompany.get_by_company_id_and_email(1, "janedoe@example.com")

        assert user_company
        assert user_company.company_id == company.id


def test_get_company_members(new_user_oauth, new_company, new_user_company, app):
    with app.app_context():
        user = User.get_by_id(1)
        user_company = db.session.scalar(db.select(UserCompany).where(UserCompany.id == 1))
        company_members = UserCompany.get_members(1)

        assert user_company
        assert user_company.user_id == user.id  # type: ignore
        assert any(member_user.id == user.id for member_user, _ in company_members)  # type: ignore


def test_get_all_user_companies(new_user_oauth, new_company, new_user_company, app):
    with app.app_context():
        user_companies = UserCompany.get_all()
        assert user_companies


def test_set_primary(new_user_oauth, new_company, new_user_company, app):
    with app.app_context():
        user_company = db.session.scalar(db.select(UserCompany).where(UserCompany.id == 1))
        user = User.get_by_id(1)

        assert user
        assert not user_company.is_primary

        user_company.set_primary = user.id

        assert user_company.is_primary


def test_get_primary_by_user_id(new_user_oauth, new_company, new_user_company, app):
    with app.app_context():
        user = User.get_by_id(1)
        assert user

        user_company = db.session.scalar(db.select(UserCompany).where(UserCompany.id == 1))
        user_company.set_primary = user.id

        test_user_company = UserCompany.get_primary_by_user_id(1)

        assert test_user_company


def test_get_claim_request_by_id(new_user_oauth, new_claim_request, app):
    with app.app_context():
        claim_request = ClaimRequest.get_by_id(1)

        assert claim_request
        assert claim_request.email == "jane@example.com"


def test_get_claim_request_by_user_id(new_user_oauth, new_claim_request, app):
    with app.app_context():
        claim_request = ClaimRequest.get_by_user_id(1)

        assert claim_request
        assert claim_request.user_id == 1
        assert claim_request.email == "jane@example.com"


def test_get_claim_request_by_investor_id(new_user_oauth, new_claim_request, app):
    with app.app_context():
        claim_request = ClaimRequest.get_by_investor_id(1)

        assert claim_request
        assert claim_request.investor_id == 1
        assert claim_request.email == "jane@example.com"


def test_get_all_claim_requests(new_user_oauth, new_claim_request, app):
    with app.app_context():
        claim_requests = ClaimRequest.get_all()

        assert claim_requests
        assert len(claim_requests) == 1
        assert claim_requests[0].email == "jane@example.com"
