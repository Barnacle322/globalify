import pytest

from ...project import db
from ...project.models import Industry, InvestmentFirm, Investor, Round


@pytest.fixture()
def new_investor(app):
    with app.app_context():
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
            phone_number="+999123123123",
            n_investments=3,
            n_exits=2,
            min_investment="$100k",
            max_investment="$50M",
            location="Germany",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
        )
        db.session.add(investor)
        db.session.commit()


@pytest.fixture()
def new_investment_firm(app):
    with app.app_context():
        investment_firm = InvestmentFirm(
            name="BlackRock",
            about="Global investment firm",
            website="https://blakcrock.com",
            email="belux@blackrock.com",
            phone_number="31-20-549-5200",
            n_investments=999,
            n_exits=999,
            n_employees=999,
            min_investment="$999M",
            max_investment="$999T",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
        )
        db.session.add(investment_firm)
        db.session.commit()


def test_investor(new_investor, app):
    with app.app_context():
        investor = Investor.query.first()
        assert investor
        assert investor.first_name == "Jane"
        assert investor.last_name == "Doe"
        assert investor.firm_name == "BerkshireHathaway"
        assert investor.about == "Passionate investor"
        assert investor.position == "Investment Analyst"
        assert investor.website == "https://berkshire.com"
        assert investor.linkedin == "linkedin_acc"
        assert investor.twitter == "twitter_acc"
        assert investor.email == "jane@example.com"
        assert investor.phone_number == "+999123123123"
        assert investor.n_investments == 3
        assert investor.n_exits == 2
        assert investor.min_investment == "$100k"
        assert investor.max_investment == "$50M"
        assert investor.location == "Germany"
        assert investor.rounds == [Round.get_by_id(1)]
        assert investor.industries == [Industry.get_by_id(1)]


def test_investment_firm(new_investment_firm, app):
    with app.app_context():
        investment_firm = InvestmentFirm.query.first()
        assert investment_firm
        assert investment_firm.name == "BlackRock"
        assert investment_firm.about == "Global investment firm"
        assert investment_firm.website == "https://blakcrock.com"
        assert investment_firm.email == "belux@blackrock.com"
        assert investment_firm.phone_number == "31-20-549-5200"
        assert investment_firm.n_investments == 999
        assert investment_firm.n_exits == 999
        assert investment_firm.min_investment == "$999M"
        assert investment_firm.max_investment == "$999T"
        assert investment_firm.rounds == [Round.get_by_id(1)]
        assert investment_firm.industries == [Industry.get_by_id(1)]
