import pytest
from flask_sqlalchemy.pagination import Pagination

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
            min_investment=100000,
            max_investment=50000000,
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


@pytest.fixture()
def create_investors_with_rounds(app):
    with app.app_context():
        round_2 = Round.get_by_id(2)
        round_3 = Round.get_by_id(3)

        assert round_2 and round_3

        investor_with_round_2 = Investor(first_name="Investor1", rounds=[round_2])
        investor_with_round_3 = Investor(first_name="Investor2", rounds=[round_3])
        investor_with_both_rounds = Investor(first_name="Investor3", rounds=[round_2, round_3])

        db.session.add_all([investor_with_round_2, investor_with_round_3, investor_with_both_rounds])
        db.session.commit()


@pytest.fixture()
def create_investors_with_industries(app):
    with app.app_context():
        industry_2 = Industry.get_by_id(2)
        industry_3 = Industry.get_by_id(3)

        assert industry_2 and industry_3

        investor_with_industry_1 = Investor(first_name="Investor1", industries=[industry_2])
        investor_with_industry_2 = Investor(first_name="Investor2", industries=[industry_3])
        investor_with_both_industries = Investor(first_name="Investor3", industries=[industry_2, industry_3])

        db.session.add_all([investor_with_industry_1, investor_with_industry_2, investor_with_both_industries])
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
        assert investor.rounds == [Round.get_by_id(1)]
        assert investor.industries == [Industry.get_by_id(1)]


@pytest.fixture()
def populate_investor(app):
    with app.app_context():
        Investor.populate()


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


def test_pagination(populate_investor, app):
    with app.app_context():
        page_size = 10
        page_number = 1

        paginated_investors_1 = Investor.get_pagination(page=page_number, per_page=page_size)
        paginated_investors_2 = Investor.get_pagination(page=page_number, per_page=page_size)

        assert isinstance(paginated_investors_1, Pagination)
        assert len(paginated_investors_1.items) == page_size

        page_number = 2
        assert isinstance(paginated_investors_2, Pagination)
        assert len(paginated_investors_2.items) > 0
        assert len(paginated_investors_2.items) <= page_size


@pytest.mark.parametrize(
    "query_name, filter_field, expected_value",
    [
        ("Jane", "first_name", "Jane"),
        ("Doe", "last_name", "Doe"),
        ("BerkshireHathaway", "firm_name", "BerkshireHathaway"),
        ("Investment Analyst", "position", "Investment Analyst"),
    ],
)
def test_filtering_by_field(new_investor, app, query_name, filter_field, expected_value):
    with app.app_context():
        filtered_items = Investor.get_pagination(query=query_name, filter_fields=filter_field)

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 1
        assert getattr(filtered_items.items[0], filter_field) == expected_value


def test_search_without_filtering(new_investor, app):
    with app.app_context():
        query = "Jane"

        paginated_investors = Investor.get_pagination(query=query)

        assert isinstance(paginated_investors, Pagination)
        assert len(paginated_investors.items) >= 1

        assert any(
            query.lower() in field.lower()
            for item in paginated_investors.items
            for field in [item.first_name, item.last_name, item.firm_name, item.position]
        )


def test_filter_by_rounds_with_and_operator(app, create_investors_with_rounds):
    with app.app_context():
        round_2 = Round.get_by_id(2)
        round_3 = Round.get_by_id(3)

        assert round_2 and round_3

        paginated_investors_1 = Investor.get_pagination(rounds=[round_2], rounds_exclusive=True)
        paginated_investors_2 = Investor.get_pagination(rounds=[round_3], rounds_exclusive=True)
        paginated_investors_3 = Investor.get_pagination(rounds=[round_2, round_3], rounds_exclusive=True)

        assert isinstance(paginated_investors_1, Pagination)
        assert len(paginated_investors_1.items) == 2

        assert isinstance(paginated_investors_2, Pagination)
        assert len(paginated_investors_2.items) == 2

        assert isinstance(paginated_investors_3, Pagination)
        assert len(paginated_investors_3.items) == 1


def test_filter_by_rounds_with_or_operator(app, create_investors_with_rounds):
    with app.app_context():
        round_2 = Round.get_by_id(2)
        round_3 = Round.get_by_id(3)

        assert round_2 and round_3

        paginated_investors_1 = Investor.get_pagination(rounds=[round_2], rounds_exclusive=False)
        paginated_investors_2 = Investor.get_pagination(rounds=[round_3], rounds_exclusive=False)
        paginated_investors_3 = Investor.get_pagination(rounds=[round_2, round_3], rounds_exclusive=False)

        assert isinstance(paginated_investors_1, Pagination)
        assert len(paginated_investors_1.items) == 2

        assert isinstance(paginated_investors_2, Pagination)
        assert len(paginated_investors_2.items) == 2

        assert isinstance(paginated_investors_3, Pagination)
        assert len(paginated_investors_3.items) == 3


def test_filter_by_industries_with_and_operator(app, create_investors_with_industries):
    with app.app_context():
        industry_2 = Industry.get_by_id(2)
        industry_3 = Industry.get_by_id(3)

        assert industry_2 and industry_3

        paginated_investors_1 = Investor.get_pagination(industries=[industry_2], industries_exclusive=True)
        paginated_investors_2 = Investor.get_pagination(industries=[industry_3], industries_exclusive=True)
        paginated_investors_3 = Investor.get_pagination(industries=[industry_2, industry_3], industries_exclusive=True)

        assert isinstance(paginated_investors_1, Pagination)
        assert len(paginated_investors_1.items) == 2

        assert isinstance(paginated_investors_2, Pagination)
        assert len(paginated_investors_2.items) == 2

        assert isinstance(paginated_investors_3, Pagination)
        assert len(paginated_investors_3.items) == 1


def test_filter_by_industries_with_or_operator(app, create_investors_with_industries):
    with app.app_context():
        industry_2 = Industry.get_by_id(2)
        industry_3 = Industry.get_by_id(3)

        assert industry_2 and industry_3

        paginated_investors_1 = Investor.get_pagination(industries=[industry_2], industries_exclusive=False)
        paginated_investors_2 = Investor.get_pagination(industries=[industry_3], industries_exclusive=False)
        paginated_investors_3 = Investor.get_pagination(industries=[industry_2, industry_3], industries_exclusive=False)

        assert isinstance(paginated_investors_1, Pagination)
        assert len(paginated_investors_1.items) == 2

        assert isinstance(paginated_investors_2, Pagination)
        assert len(paginated_investors_2.items) == 2

        assert isinstance(paginated_investors_3, Pagination)
        assert len(paginated_investors_3.items) == 3


@pytest.mark.parametrize(
    "sort_field",
    [
        "first_name",
        "last_name",
        "firm_name",
        "position",
    ],
)
def test_apply_sorting_by_field(populate_investor, app, sort_field):
    with app.app_context():
        paginated_investors_1 = Investor.get_pagination(sort_field=sort_field, descending=False)
        paginated_investors_2 = Investor.get_pagination(sort_field=sort_field, descending=True)

        assert isinstance(paginated_investors_1, Pagination)
        assert len(paginated_investors_1.items) > 1

        for i in range(len(paginated_investors_1.items) - 1):
            current_value = getattr(paginated_investors_1.items[i], sort_field)
            next_value = getattr(paginated_investors_1.items[i + 1], sort_field)
            assert current_value <= next_value

        assert isinstance(paginated_investors_2, Pagination)
        assert len(paginated_investors_2.items) > 1

        for i in range(len(paginated_investors_2.items) - 1):
            current_value = getattr(paginated_investors_2.items[i], sort_field)
            next_value = getattr(paginated_investors_2.items[i + 1], sort_field)
            assert current_value >= next_value


def test_sorting_by_nonexistent_field(populate_investor, app):
    with app.app_context():
        page_size = 10
        nonexistent_field = "nonexistent_field"

        paginated_investors = Investor.get_pagination(sort_field=nonexistent_field)

        assert isinstance(paginated_investors, Pagination)
        assert len(paginated_investors.items) > 0
        assert len(paginated_investors.items) == page_size


# failed tests


def test_filtering_wrong_query_name(new_investor, app):
    with app.app_context():
        filtered_items = Investor.get_pagination(query="NonExistentName", filter_fields=["first_name"])
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 0


def test_filtering_wrong_filter_field(new_investor, app):
    with app.app_context():
        filtered_items = Investor.get_pagination(query="Jane", filter_fields=["nonexistent_field"])

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 1


def test_filtering_invalid_query_and_field_combination(new_investor, app):
    with app.app_context():
        filtered_items = Investor.get_pagination(query="BerkshireHathaway", filter_fields=["position"])

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 0


# def test_filtering_no_results_for_valid_query_and_field(new_investor, app):
#     """
#     need to fix this case in get_pagination, found bugs
#     """
#     with app.app_context():
#         filtered_items = Investor.get_pagination(query="NonExistentName", filter_fields=["nonexistent_field"])
#         print(filtered_items.items)
#         assert isinstance(filtered_items, Pagination)
#         assert len(filtered_items.items) == 0
