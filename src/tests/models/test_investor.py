import pytest
from flask_sqlalchemy.pagination import Pagination

from src.project.models.investor import SuggestionBuilder
from src.project.models.user import Company

from ...project import db
from ...project.models import Industry, Investor, NotableInvestment, Round


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
def new_investors_with_rounds(app):
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
def new_investors_with_industries(app):
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


@pytest.fixture()
def populate_notable_investment(app):
    with app.app_context():
        NotableInvestment.populate()


def test_pagination(populate_notable_investment, populate_investor, app):
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
        filtered_items = Investor.get_pagination(search_string=query_name, filter_fields=filter_field)

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 1
        assert getattr(filtered_items.items[0], filter_field) == expected_value


def test_search_without_filtering(new_investor, app):
    with app.app_context():
        query = "Jane"

        paginated_investors = Investor.get_pagination(search_string=query)

        assert isinstance(paginated_investors, Pagination)
        assert len(paginated_investors.items) >= 1

        assert any(
            query.lower() in field.lower()
            for item in paginated_investors.items
            for field in [item.first_name, item.last_name, item.firm_name, item.position]
        )


def test_filter_by_rounds_with_and_operator(app, new_investors_with_rounds):
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


def test_filter_by_rounds_with_or_operator(app, new_investors_with_rounds):
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


def test_filter_by_industries_with_and_operator(app, new_investors_with_industries):
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


def test_filter_by_industries_with_or_operator(app, new_investors_with_industries):
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
def test_apply_sorting_by_field(populate_notable_investment, populate_investor, app, sort_field):
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


def test_sorting_by_nonexistent_field(populate_notable_investment, populate_investor, app):
    with app.app_context():
        page_size = 10
        nonexistent_field = "nonexistent_field"

        paginated_investors = Investor.get_pagination(sort_field=nonexistent_field)

        assert isinstance(paginated_investors, Pagination)
        assert len(paginated_investors.items) > 0
        assert len(paginated_investors.items) == page_size


# failing tests


def test_filtering_wrong_query_name(populate_notable_investment, populate_investor, app):
    with app.app_context():
        filtered_items = Investor.get_pagination(search_string="NonExistentName", filter_fields=["first_name"])
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 0


def test_filtering_wrong_filter_field(populate_notable_investment, populate_investor, app):
    with app.app_context():
        page_size = 10
        filtered_items = Investor.get_pagination(search_string="Jane", filter_fields=["nonexistent_field"])

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == page_size


def test_filtering_invalid_query_and_field_combination(new_investor, app):
    with app.app_context():
        filtered_items = Investor.get_pagination(search_string="BerkshireHathaway", filter_fields=["position"])

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 0


def test_filtering_for_invalid_query_and_field(populate_notable_investment, populate_investor, app):
    with app.app_context():
        page_size = 10
        filtered_items = Investor.get_pagination(search_string="NonExistentName", filter_fields=["nonexistent_field"])

        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == page_size


def test_filter_by_empty_rounds_list(app, populate_notable_investment, populate_investor):
    with app.app_context():
        page_size = 10
        filtered_items = Investor.get_pagination(rounds=[], rounds_exclusive=True)
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == page_size


def test_filter_by_nonexistent_round(app, populate_notable_investment, populate_investor):
    with app.app_context():
        non_existing_round = Round(id=100, name="NonExistingRound")
        filtered_items = Investor.get_pagination(rounds=[non_existing_round], rounds_exclusive=True)
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 0


def test_filter_by_empty_industries_list(app, populate_notable_investment, populate_investor):
    with app.app_context():
        page_size = 10
        filtered_items = Investor.get_pagination(industries=[], industries_exclusive=True)
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == page_size


def test_filter_by_nonexistent_industry(app, populate_notable_investment, populate_investor):
    with app.app_context():
        non_existing_industry = Industry(id=100, name="NonExistingIndustry")
        filtered_items = Investor.get_pagination(industries=[non_existing_industry], industries_exclusive=True)
        assert isinstance(filtered_items, Pagination)
        assert len(filtered_items.items) == 0


@pytest.fixture()
def suggestion_builder_data():
    investor_list = [
        {
            "id": 1,
            "first_name": "John",
            "last_name": "Doe",
            "firm_name": "BlackRock",
            "about": "About John",
            "position": "CEO",
            "website": "https://www.blackrock.com",
            "linkedin": "https://www.linkedin.com/in/John",
            "twitter": "https://www.twitter.com/john",
            "email": "johndoe@example.com",
            "phone_number": "+11806123274",
            "n_investments": 107,
            "n_exits": 41,
            "min_investment": 100000,
            "max_investment": 50000000,
            "location": "Grenada",
            "coordinates": "33.7816,-89.813",
            "country": "United States",
            "bias": 50,
            "industries": ["Technology", "Finance"],
            "rounds": ["Series A", "Series B"],
            "preferred_round": "Series B",
        },
        {
            "id": 2,
            "first_name": "Jane",
            "last_name": "Doe",
            "firm_name": "Amazon",
            "about": "About Jane",
            "position": "CFO",
            "website": "https://www.amazon.com",
            "linkedin": "https://www.linkedin.com/in/Jane",
            "twitter": "https://www.twitter.com/jane",
            "email": "janedoe@example.com",
            "phone_number": "+11806921574",
            "n_investments": 96,
            "n_exits": 35,
            "min_investment": 200000,
            "max_investment": 80000000,
            "location": "Spain",
            "coordinates": "39.3669,-3.355",
            "country": "Spain",
            "bias": 43,
            "industries": ["Agriculture", "Healthcare"],
            "rounds": ["Series A", "Series C"],
            "preferred_round": "Series C",
        },
        {
            "id": 3,
            "first_name": "Bob",
            "last_name": "Doe",
            "firm_name": "Apple",
            "about": "About Bob",
            "position": "CTO",
            "website": "https://www.apple.com",
            "linkedin": "https://www.linkedin.com/in/Bob",
            "twitter": "https://www.twitter.com/bob",
            "email": "bobdoe@example.com",
            "phone_number": "+11806123574",
            "n_investments": 86,
            "n_exits": 25,
            "min_investment": 300000,
            "max_investment": 90000000,
            "location": "Nepal",
            "coordinates": "29.25,82.2167",
            "country": "Nepal",
            "bias": 60,
            "industries": ["AI", "Blockchain"],
            "rounds": ["Series A", "Series C"],
            "preferred_round": "Series C",
        }
    ]
    return investor_list


@pytest.fixture
def sample_company():
    return Company(
        name="Sample Company",
        industry=Industry(name="Tech"),
        preferred_round=Round(name="Series A"),
        coordinates="37.7749,-122.4194"  # Coordinates of San Francisco
    )


@pytest.fixture()
def suggestion_builder_instance(suggestion_builder_data, sample_company):
    return SuggestionBuilder(investor_list=suggestion_builder_data, company=sample_company)


def test_suggestion_builder(suggestion_builder_instance):
    assert isinstance(suggestion_builder_instance, SuggestionBuilder)
    assert isinstance(suggestion_builder_instance.investor_list, list)
    assert len(suggestion_builder_instance.investor_list) == 3


def test_calculate_all_scores(suggestion_builder_instance):
    suggestion_builder_instance.calculate_all_scores()
    investors = suggestion_builder_instance.investor_list

    assert investors[0]["total_score"] == pytest.approx(0.4789, 0.001)
    assert investors[1]["total_score"] == pytest.approx(0.3771, 0.001)
    assert investors[2]["total_score"] == pytest.approx(0.3943, 0.001)


def test_sort_by_score(suggestion_builder_instance):
    suggestion_builder_instance.calculate_all_scores()
    suggestion_builder_instance.sort_by_score()
    investors = suggestion_builder_instance.investor_list

    assert investors[0]["id"] == 1
    assert investors[1]["id"] == 3
    assert investors[2]["id"] == 2


def test_get_id_list(suggestion_builder_data, sample_company):

    suggestion_builder = SuggestionBuilder(investor_list=suggestion_builder_data, company=sample_company)
    suggestion_builder.calculate_all_scores()
    suggestion_builder.sort_by_score()

    id_list = suggestion_builder.get_id_list(quantity=1)

    assert len(id_list) == 1
    assert id_list[0] == 1
