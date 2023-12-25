import pytest
from flask_sqlalchemy.pagination import Pagination

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
        )
        db.session.add(investment_firm)
        db.session.commit()


@pytest.fixture()
def new_investment_firms_with_rounds(app):
    with app.app_context():
        round_2 = Round.get_by_id(2)
        round_3 = Round.get_by_id(3)

        assert round_2 and round_3

        investment_firm_with_round_2 = InvestmentFirm(name="InvestmentFirm1", rounds=[round_2])
        investment_firm_with_round_3 = InvestmentFirm(name="InvestmentFirm2", rounds=[round_3])
        investment_firm_with_both_rounds = InvestmentFirm(name="InvestmentFirm3", rounds=[round_2, round_3])

        db.session.add_all([investment_firm_with_round_2, investment_firm_with_round_3, investment_firm_with_both_rounds])
        db.session.commit()


@pytest.fixture()
def new_investment_firms_with_industries(app):
    with app.app_context():
        industry_2 = Industry.get_by_id(2)
        industry_3 = Industry.get_by_id(3)

        assert industry_2 and industry_3

        investment_firm_with_industry_1 = InvestmentFirm(name="InvestmentFirm1", industries=[industry_2])
        investment_firm_with_industry_2 = InvestmentFirm(name="InvestmentFirm2", industries=[industry_3])
        investment_firm_with_both_industries = InvestmentFirm(name="InvestmentFirm3", industries=[industry_2, industry_3])

        db.session.add_all([investment_firm_with_industry_1, investment_firm_with_industry_2, investment_firm_with_both_industries])
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


def test_pagination(populate_investment_firm, app):
    with app.app_context():
        page_size = 10
        page_number = 1

        paginated_investment_firms_1 = InvestmentFirm.get_pagination(page=page_number, per_page=page_size)
        paginated_investment_firms_2 = InvestmentFirm.get_pagination(page=page_number, per_page=page_size)

        assert isinstance(paginated_investment_firms_1, Pagination)
        assert len(paginated_investment_firms_1.items) == page_size

        page_number = 2
        assert isinstance(paginated_investment_firms_2, Pagination)
        assert len(paginated_investment_firms_2.items) > 0
        assert len(paginated_investment_firms_2.items) <= page_size


@pytest.mark.parametrize(
    "query_name, filter_field, expected_value",
    [
        ("BlackRock", "name", "BlackRock"),
        ("Global investment firm", "about", "Global investment firm"),
    ],
)
def test_filtering_by_field(new_investment_firm, app, query_name, filter_field, expected_value):
    with app.app_context():
        filtered_items = InvestmentFirm.get_pagination(query=query_name, filter_fields=filter_field)

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 1
        assert getattr(filtered_items.items[0], filter_field) == expected_value


def test_search_without_filtering(new_investment_firm, app):
    with app.app_context():
        query = "BlackRock"

        paginated_investment_firms = InvestmentFirm.get_pagination(query=query)

        assert isinstance(paginated_investment_firms, Pagination)
        assert len(paginated_investment_firms.items) >= 1

        assert any(
            query.lower() in field.lower()
            for item in paginated_investment_firms.items
            for field in [item.name, item.about]
        )


def test_filter_by_rounds_with_and_operator(app, new_investment_firms_with_rounds):
    with app.app_context():
        round_2 = Round.get_by_id(2)
        round_3 = Round.get_by_id(3)

        assert round_2 and round_3

        paginated_investment_firms_1 = InvestmentFirm.get_pagination(rounds=[round_2], rounds_exclusive=True)
        paginated_investment_firms_2 = InvestmentFirm.get_pagination(rounds=[round_3], rounds_exclusive=True)
        paginated_investment_firms_3 = InvestmentFirm.get_pagination(rounds=[round_2, round_3], rounds_exclusive=True)

        assert isinstance(paginated_investment_firms_1, Pagination)
        assert len(paginated_investment_firms_1.items) == 2

        assert isinstance(paginated_investment_firms_2, Pagination)
        assert len(paginated_investment_firms_2.items) == 2

        assert isinstance(paginated_investment_firms_3, Pagination)
        assert len(paginated_investment_firms_3.items) == 1


def test_filter_by_rounds_with_or_operator(app, new_investment_firms_with_rounds):
    with app.app_context():
        round_2 = Round.get_by_id(2)
        round_3 = Round.get_by_id(3)

        assert round_2 and round_3

        paginated_investment_firms_1 = InvestmentFirm.get_pagination(rounds=[round_2], rounds_exclusive=False)
        paginated_investment_firms_2 = InvestmentFirm.get_pagination(rounds=[round_3], rounds_exclusive=False)
        paginated_investment_firms_3 = InvestmentFirm.get_pagination(rounds=[round_2, round_3], rounds_exclusive=False)

        assert isinstance(paginated_investment_firms_1, Pagination)
        assert len(paginated_investment_firms_1.items) == 2

        assert isinstance(paginated_investment_firms_2, Pagination)
        assert len(paginated_investment_firms_2.items) == 2

        assert isinstance(paginated_investment_firms_3, Pagination)
        assert len(paginated_investment_firms_3.items) == 3


def test_filter_by_industries_with_and_operator(app, new_investment_firms_with_industries):
    with app.app_context():
        industry_2 = Industry.get_by_id(2)
        industry_3 = Industry.get_by_id(3)

        assert industry_2 and industry_3

        paginated_investment_firms_1 = InvestmentFirm.get_pagination(industries=[industry_2], industries_exclusive=True)
        paginated_investment_firms_2 = InvestmentFirm.get_pagination(industries=[industry_3], industries_exclusive=True)
        paginated_investment_firms_3 = InvestmentFirm.get_pagination(industries=[industry_2, industry_3], industries_exclusive=True)

        assert isinstance(paginated_investment_firms_1, Pagination)
        assert len(paginated_investment_firms_1.items) == 2

        assert isinstance(paginated_investment_firms_2, Pagination)
        assert len(paginated_investment_firms_2.items) == 2

        assert isinstance(paginated_investment_firms_3, Pagination)
        assert len(paginated_investment_firms_3.items) == 1


def test_filter_by_industries_with_or_operator(app, new_investment_firms_with_industries):
    with app.app_context():
        industry_2 = Industry.get_by_id(2)
        industry_3 = Industry.get_by_id(3)

        assert industry_2 and industry_3

        paginated_investment_firms_1 = InvestmentFirm.get_pagination(industries=[industry_2], industries_exclusive=False)
        paginated_investment_firms_2 = InvestmentFirm.get_pagination(industries=[industry_3], industries_exclusive=False)
        paginated_investment_firms_3 = InvestmentFirm.get_pagination(industries=[industry_2, industry_3], industries_exclusive=False)

        assert isinstance(paginated_investment_firms_1, Pagination)
        assert len(paginated_investment_firms_1.items) == 2

        assert isinstance(paginated_investment_firms_2, Pagination)
        assert len(paginated_investment_firms_2.items) == 2

        assert isinstance(paginated_investment_firms_3, Pagination)
        assert len(paginated_investment_firms_3.items) == 3


@pytest.mark.parametrize(
    "sort_field",
    [
        "name",
        "about",
    ],
)
def test_apply_sorting_by_field(populate_investment_firm, app, sort_field):
    with app.app_context():
        paginated_investment_firms_1 = InvestmentFirm.get_pagination(sort_field=sort_field, descending=False)
        paginated_investment_firms_2 = InvestmentFirm.get_pagination(sort_field=sort_field, descending=True)

        assert isinstance(paginated_investment_firms_1, Pagination)
        assert len(paginated_investment_firms_1.items) > 1

        for i in range(len(paginated_investment_firms_1.items) - 1):
            current_value = getattr(paginated_investment_firms_1.items[i], sort_field)
            next_value = getattr(paginated_investment_firms_1.items[i + 1], sort_field)
            assert current_value <= next_value

        assert isinstance(paginated_investment_firms_2, Pagination)
        assert len(paginated_investment_firms_2.items) > 1

        for i in range(len(paginated_investment_firms_2.items) - 1):
            current_value = getattr(paginated_investment_firms_2.items[i], sort_field)
            next_value = getattr(paginated_investment_firms_2.items[i + 1], sort_field)
            assert current_value >= next_value


def test_sorting_by_nonexistent_field(populate_investment_firm, app):
    with app.app_context():
        page_size = 10
        nonexistent_field = "nonexistent_field"

        paginated_investment_firms = InvestmentFirm.get_pagination(sort_field=nonexistent_field)

        assert isinstance(paginated_investment_firms, Pagination)
        assert len(paginated_investment_firms.items) > 0
        assert len(paginated_investment_firms.items) == page_size


# failing tests


def test_filtering_wrong_query_name(populate_investment_firm, app):
    with app.app_context():
        filtered_items = InvestmentFirm.get_pagination(query="NonExistentName", filter_fields=["name"])
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 0


def test_filtering_wrong_filter_field(populate_investment_firm, app):
    with app.app_context():
        page_size = 10
        filtered_items = InvestmentFirm.get_pagination(query="BlackRock", filter_fields=["nonexistent_field"])

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == page_size


def test_filtering_invalid_query_and_field_combination(new_investment_firm, app):
    with app.app_context():
        filtered_items = InvestmentFirm.get_pagination(query="BlackRock", filter_fields=["about"])

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 0


def test_filtering_for_invalid_query_and_field(populate_investment_firm, app):
    with app.app_context():
        page_size = 10
        filtered_items = InvestmentFirm.get_pagination(query="NonExistentName", filter_fields=["nonexistent_field"])

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == page_size


def test_filter_by_empty_rounds_list(app, populate_investment_firm):
    with app.app_context():
        page_size = 10
        filtered_items = InvestmentFirm.get_pagination(rounds=[], rounds_exclusive=True)
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == page_size


def test_filter_by_nonexistent_round(app, populate_investment_firm):
    with app.app_context():
        non_existing_round = Round(id=100, name="NonExistingRound")
        filtered_items = InvestmentFirm.get_pagination(rounds=[non_existing_round], rounds_exclusive=True)
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 0



def test_filter_by_empty_industries_list(app, populate_investment_firm):
    with app.app_context():
        page_size = 10
        filtered_items = InvestmentFirm.get_pagination(industries=[], industries_exclusive=True)
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == page_size


def test_filter_by_nonexistent_industry(app, populate_investment_firm):
    with app.app_context():
        non_existing_industry = Industry(id=100, name="NonExistingIndustry")
        filtered_items = InvestmentFirm.get_pagination(industries=[non_existing_industry], industries_exclusive=True)
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 0
