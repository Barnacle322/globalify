import pytest

from ...project import db
from ...project.models import Company, Industry, InvestmentFirm, NotableInvestment, Round


@pytest.fixture()
def new_investment_firm_with_additional_info(app):
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
            bias=15,
        )
        db.session.add(investment_firm)
        db.session.commit()


@pytest.fixture()
def new_investment_firm_without_additional_infos_with_additional_info(app):
    with app.app_context():
        investment_firm1 = InvestmentFirm(
            name="BlueRock",
            about="Global investment firm",
            website="https://bluecrock.com",
            email="belux@bluekrock.com",
            phone_number="21-23-149-5200",
            n_investments=999,
            n_exits=999,
            n_employees=999,
            min_investment=100000,
            max_investment=50000000,
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            location="Antwerp",
            _country="Berlin",
            bias=12,
        )

        investment_firm2 = InvestmentFirm(
            name="Acme Ventures",
            about="Early-stage venture capital firm",
            website="https://acme.vc",
            email="info@acme.vc",
            phone_number="1-415-555-1234",
            n_investments=50,
            n_exits=20,
            n_employees=25,
            min_investment=50000,
            max_investment=5000000,
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            location="San Francisco",
            _country="USA",
            bias=None,
        )
        db.session.add_all([investment_firm1, investment_firm2])
        db.session.commit()


@pytest.fixture()
def populate_investment_firm(app):
    with app.app_context():
        NotableInvestment.populate()
        InvestmentFirm.populate()


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


def test_investment_firm(new_investment_firm_with_additional_info, app):
    with app.app_context():
        investment_firm = db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.id == 1))
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
        assert investment_firm.bias == 15


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


def test_get_by_email_existings(new_investment_firm_with_additional_info, app):
    with app.app_context():
        investment_firm = InvestmentFirm.get_by_email("belux@blackrock.com")
        assert investment_firm
        assert investment_firm.email == "belux@blackrock.com"


def test_get_by_email_non_existings(new_investment_firm_with_additional_info, app):
    with app.app_context():
        investment_firm = InvestmentFirm.get_by_email("delux@blackrock.com")
        assert not investment_firm


def test_get_by_id_existing(new_investment_firm_with_additional_info, app):
    with app.app_context():
        investor_firm = InvestmentFirm.get_by_id(1)
        assert investor_firm
        assert investor_firm.id == 1


def test_get_by_id_list(new_investment_firm_without_additional_infos_with_additional_info, app):
    with app.app_context():
        investor_firm = InvestmentFirm.get_by_id_list([1, 2])
        assert investor_firm
        assert investor_firm[0].name == "BlueRock"
        assert investor_firm[1].name == "Acme Ventures"


def test_get_by_id_non_existing(new_investment_firm_with_additional_info, app):
    with app.app_context():
        investor_firm = InvestmentFirm.get_by_id(999)
        assert not investor_firm


def test_slugify_existing_investment_firms(new_investment_firm_with_additional_info, app):
    with app.app_context():
        investor_firm = db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.id == 1))
        assert not investor_firm.slug

        InvestmentFirm.slugify_existing()

        assert investor_firm.slug == "blackrock"


def test_calculate_investment_firm_bias_score(new_investment_firm_with_additional_info, app):
    with app.app_context():
        investor_firm = db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.id == 1))
        bias_score = InvestmentFirm.calculate_bias_score(investor_firm)

        assert bias_score
        assert bias_score == 0.15


# def test_calculate_investment_firm_bias_score_with_error(new_investment_firm_without_additional_infos_with_additional_info, app):
#     with app.app_context():
#         investor_firm = db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.id == 2))
#         print(investor_firm)
#         with pytest.raises(TypeError) as e:
#             bias_score = InvestmentFirm.calculate_bias_score(investor_firm)

#         assert not bias_score
#         assert (
#             str(e.value)
#             == "An error occurred while calculating the score: unsupported operand type(s) for /: 'NoneType' and 'int'"
#         )


def test_calculate_investment_firm_bias_score_non_existing(
    new_investment_firm_without_additional_infos_with_additional_info, app
):
    with app.app_context():
        investor_firm = db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.id == 1))
        bias_score = InvestmentFirm.calculate_bias_score(investor_firm)

        assert bias_score == 0.12


def test_calculate_investment_firm_exits_score(new_investment_firm_with_additional_info, app):
    with app.app_context():
        investor_firm = db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.id == 1))
        exits_score = InvestmentFirm.calculate_exits_score(investor_firm)

        assert exits_score
        assert exits_score == 1


def test_calculate_investment_firm_exits_score_with_zero_exits(
    new_investment_firm_without_additional_infos_with_additional_info, app
):
    with app.app_context():
        investor_firm = db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.id == 1))
        exits_score = InvestmentFirm.calculate_exits_score(investor_firm)

        assert exits_score == 1


def test_calculate_investment_firm_completeness_score(new_investment_firm_with_additional_info, app):
    with app.app_context():
        investor_firm = db.session.scalar(db.select(InvestmentFirm).where(InvestmentFirm.id == 1))
        completness_score = InvestmentFirm.calculate_completeness_score(investor_firm)

    assert completness_score > 0.5


def test_get_investment_firm_suggestions(
    new_company,
    new_investment_firm_with_additional_info,
    new_investment_firm_without_additional_infos_with_additional_info,
    app,
):
    with app.app_context():
        company = Company.get_by_id(1)
        suggestions = InvestmentFirm.get_suggestions(company, 3)  # type: ignore
        print(suggestions)
        assert suggestions
        assert len(suggestions) == 3
        assert "<InvestmentFirm Acme Ventures>" in str(suggestions)
        assert suggestions[1].email == "belux@bluekrock.com"
        assert suggestions[2].max_investment == 5000000


def test_min_max_investment(new_investment_firm_without_additional_infos_with_additional_info, app):
    with app.app_context():
        investment_firm = InvestmentFirm.get_by_id(1)
        assert investment_firm

        min_max = investment_firm.min_max_investment
        assert min_max == "$100,000 - $50,000,000"
