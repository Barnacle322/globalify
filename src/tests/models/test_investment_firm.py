import pytest

from ...project import db
from ...project.models import Industry, InvestmentFirm, Round


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
            min_investment=100000,
            max_investment=50000000,
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            location="Antwerp",
            _country="Berlin",
        )
        db.session.add(investment_firm)
        db.session.commit()


@pytest.fixture()
def populate_investment_firm(app):
    with app.app_context():
        InvestmentFirm.populate()


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
        assert investment_firm.min_investment == 100000
        assert investment_firm.max_investment == 50000000
        assert investment_firm.rounds == [Round.get_by_id(1)]
        assert investment_firm.industries == [Industry.get_by_id(1)]
        assert investment_firm.location == "Antwerp"
        assert investment_firm._country == "Berlin"


def test_get_all_investment_firm(populate_investment_firm, app):
    with app.app_context():
        investment_firm = InvestmentFirm.get_all()

        assert len(investment_firm) == 49
        assert investment_firm

        assert investment_firm[0].id == 1
        assert investment_firm[1].id == 2
        assert investment_firm[2].id == 3
        assert investment_firm[3].id == 4
        assert investment_firm[4].id == 5
        assert investment_firm[5].id == 6
        assert investment_firm[6].id == 7
        assert investment_firm[7].id == 8
        assert investment_firm[8].id == 9


def test_get_by_email_existings(new_investment_firm, app):
    with app.app_context():
        investment_firm = InvestmentFirm.get_by_email("belux@blackrock.com")
        assert investment_firm
        assert investment_firm.email == "belux@blackrock.com"


def test_get_by_email_non_existings(new_investment_firm, app):
    with app.app_context():
        investment_firm = InvestmentFirm.get_by_email("delux@blackrock.com")
        assert not investment_firm


def test_get_by_id_existing(new_investment_firm, app):
    with app.app_context():
        investor_firm = InvestmentFirm.get_by_id(1)
        assert investor_firm
        assert investor_firm.id == 1


def test_get_by_id_non_existing(new_investment_firm, app):
    with app.app_context():
        investor_firm = InvestmentFirm.get_by_id(999)
        assert not investor_firm
