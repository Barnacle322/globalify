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


def test_pagination(new_investor, app):
    with app.app_context():
        Investor.populate()
        page_size = 10
        page_number = 1
        paginated_investors = Investor.get_pagination(page=page_number, per_page=page_size)
        assert len(paginated_investors.items) == page_size

        page_number = 2
        paginated_investors = Investor.get_pagination(page=page_number, per_page=page_size)
        assert len(paginated_investors.items) > 0
        assert len(paginated_investors.items) <= page_size


@pytest.mark.parametrize("query_name, filter_field, expected_value", [
    ("Jane", "first_name", "Jane"),
    ("Doe", "last_name", "Doe"),
    ("BerkshireHathaway", "firm_name", "BerkshireHathaway"),
    ("Investment Analyst", "position", "Investment Analyst"),
])
def test_filtering_by_field(new_investor, app, query_name, filter_field, expected_value):
    with app.app_context():
        filtered_items = Investor.get_pagination(query=query_name, filter_field=filter_field)
        assert len(filtered_items.items) == 1
        assert getattr(filtered_items.items[0], filter_field) == expected_value


def test_search_without_filtering(new_investor, app):
    with app.app_context():
        query_name = "Jane"

        search_results = Investor.get_pagination(query=query_name)

        assert len(search_results.items) >= 1

        found = any(
            query_name.lower() in field.lower()
            for item in search_results.items
            for field in [item.first_name, item.last_name, item.firm_name, item.position]
        )
        assert found is True


def test_filter_by_rounds(new_investor, app):
    with app.app_context():
        round_2 = Round.get_by_id(2)
        round_3 = Round.get_by_id(3)

        investor_with_round_1 = Investor(
            first_name="Investor1",
            rounds=[round_2]
        )
        investor_with_round_2 = Investor(
            first_name="Investor2",
            rounds=[round_3]
        )
        investor_with_both_rounds = Investor(
            first_name="Investor3",
            rounds=[round_2, round_3]
        )

        db.session.add_all([investor_with_round_1, investor_with_round_2, investor_with_both_rounds])
        db.session.commit()

        filtered_by_round_2 = Investor.get_pagination(rounds=[round_2])
        assert len(filtered_by_round_2.items) == 2


        filtered_by_round_3 = Investor.get_pagination(rounds=[round_3])
        assert len(filtered_by_round_3.items) == 2

        filtered_by_both_rounds = Investor.get_pagination(rounds=[round_2, round_3])
        assert len(filtered_by_both_rounds.items) == 1


def test_filter_by_industries(new_investor, app):
    with app.app_context():
        industry_2 = Industry.get_by_id(2)
        industry_3 = Industry.get_by_id(3)

        investor_with_industry_1 = Investor(
            first_name="Investor1",
            industries=[industry_2]
        )
        investor_with_industry_2 = Investor(
            first_name="Investor2",
            industries=[industry_3]
        )
        investor_with_both_industries = Investor(
            first_name="Investor3",
            industries=[industry_2, industry_3]
        )

        db.session.add_all([investor_with_industry_1, investor_with_industry_2, investor_with_both_industries])
        db.session.commit()
        print(Investor.query.all())
        filtered_by_industry_2 = Investor.get_pagination(industries=[industry_2])
        assert len(filtered_by_industry_2.items) == 2

        filtered_by_industry_3 = Investor.get_pagination(industries=[industry_3])
        assert len(filtered_by_industry_3.items) == 2

        filtered_by_both_industries = Investor.get_pagination(industries=[industry_2, industry_3])
        assert len(filtered_by_both_industries.items) == 1


@pytest.mark.parametrize("sort_field", [
    "first_name",
    "last_name",
    "firm_name",
    "position",
])
def test_apply_sorting_by_field(new_investor, app, sort_field):
    with app.app_context():
        Investor.populate()
        sorted_items_asc = Investor.get_pagination(sort_field=sort_field, descending=False)
        assert len(sorted_items_asc.items) > 1

        for i in range(len(sorted_items_asc.items) - 1):
            current_value = getattr(sorted_items_asc.items[i], sort_field)
            next_value = getattr(sorted_items_asc.items[i + 1], sort_field)
            assert current_value <= next_value

        sorted_items_desc = Investor.get_pagination(sort_field=sort_field, descending=True)
        assert len(sorted_items_desc.items) > 1

        for i in range(len(sorted_items_desc.items) - 1):
            current_value = getattr(sorted_items_desc.items[i], sort_field)
            next_value = getattr(sorted_items_desc.items[i + 1], sort_field)
            assert current_value >= next_value
