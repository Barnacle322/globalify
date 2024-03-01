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


@pytest.fixture()
def new_notable_investment(app):
    with app.app_context():
        notable_investment1 = NotableInvestment(name="Notable Investment 1")
        notable_investment2 = NotableInvestment(name="Notable Investment 2")
        db.session.add_all([notable_investment1, notable_investment2])
        db.session.commit()


@pytest.fixture()
def populate_investor(app):
    with app.app_context():
        Investor.populate()


@pytest.fixture()
def populate_notable_investment(app):
    with app.app_context():
        NotableInvestment.populate()


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
        assert investor.notable_investments == [
            NotableInvestment.get_by_name("Notable Investment 1"),
            NotableInvestment.get_by_name("Notable Investment 2"),
        ]


def test_get_all(populate_notable_investment, populate_investor, app):
    with app.app_context():
        investors = Investor.get_all()
        assert investors
        assert len(investors) == 9

        assert investors[0].id == 1
        assert investors[1].id == 2
        assert investors[2].id == 3
        assert investors[3].id == 4
        assert investors[4].id == 5
        assert investors[5].id == 6
        assert investors[6].id == 7
        assert investors[7].id == 8
        assert investors[8].id == 9


def test_get_by_email_existing(new_investor, app):
    with app.app_context():
        investor = Investor.get_by_email("jane@example.com")
        assert investor
        assert investor.email == "jane@example.com"


def test_get_by_email_not_existing(app):
    with app.app_context():
        investor = Investor.get_by_email("johndoe@example.com")
        assert not investor


def test_get_by_id_existing(new_investor, app):
    with app.app_context():
        investor = Investor.get_by_id(1)
        assert investor
        assert investor.id == 1


def test_get_by_id_non_existing(new_investor, app):
    with app.app_context():
        investor = Investor.get_by_id(999)
        assert investor is None


def test_get_by_id_list_existing(populate_notable_investment, populate_investor, app):
    with app.app_context():
        investor_ids = [1, 2, 3]
        investors = Investor.get_by_id_list(investor_ids)
        assert investors
        assert len(investors) == 3
        assert investors[0].id == 1
        assert investors[1].id == 2
        assert investors[2].id == 3


def test_get_by_id_list_non_existing(populate_notable_investment, populate_investor, app):
    with app.app_context():
        investor_ids = [999, 123, 451]
        investors = Investor.get_by_id_list(investor_ids)
        assert investors == []


def test_get_all_notable_investments(new_notable_investment, app):
    with app.app_context():
        notable_investments = NotableInvestment.get_all()
        assert notable_investments
        assert len(notable_investments) == 2
        assert notable_investments[0].name == "Notable Investment 1"
        assert notable_investments[1].name == "Notable Investment 2"


def test_get_by_id_existing_notable_investment(new_notable_investment, app):
    with app.app_context():
        notable_investment = NotableInvestment.get_by_id(1)
        assert notable_investment
        assert notable_investment.id == 1
        assert notable_investment.name == "Notable Investment 1"


def test_get_by_id_non_existing_notable_investment(new_notable_investment, app):
    with app.app_context():
        notable_investment = NotableInvestment.get_by_id(999)
        assert notable_investment is None


def test_get_by_name_existing_notable_investment(new_notable_investment, app):
    with app.app_context():
        notable_investment = NotableInvestment.get_by_name("Notable Investment 1")
        assert notable_investment
        assert notable_investment.name == "Notable Investment 1"


def test_get_by_name_non_existing_notable_investment(new_notable_investment, app):
    with app.app_context():
        notable_investment = NotableInvestment.get_by_name("Nonexistent Investment")
        assert notable_investment is None
