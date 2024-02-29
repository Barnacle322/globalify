import pytest

from ...project import db
from ...project.models import Industry, Investor, NotableInvestment, Round


@pytest.fixture()
def new_investor(app):
    with app.app_context():
        notable_investment1 = NotableInvestment(name="Notable Investment 1")
        notable_investment2 = NotableInvestment(name="Notable Investment 2")
        db.session.add_all([notable_investment1, notable_investment2])
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
            phone_number="+999123123123",
            n_investments=3,
            n_exits=2,
            min_investment=100000,
            max_investment=50000000,
            location="Germany",
            _coordinates="20.45,16.5167",
            _country="Chad",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment1, notable_investment2],
        )
        db.session.add(investor)
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
        assert investor.min_investment == 100000
        assert investor.max_investment == 50000000
        assert investor.location == "Germany"
        assert investor._coordinates == "20.45,16.5167"
        assert investor._country == "Chad"
        assert investor.rounds == [Round.get_by_id(1)]
        assert investor.industries == [Industry.get_by_id(1)]
        assert investor.notable_investments == [NotableInvestment.get_by_name("Notable Investment 1"), NotableInvestment.get_by_name("Notable Investment 2")]
