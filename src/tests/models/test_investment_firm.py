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
