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


@pytest.fixture
def sample_company():
    return Company(
        name="Sample Company",
        industry=Industry(name="Tech"),
        preferred_round=Round(name="Series A"),
        coordinates="37.7749,-122.4194",  # Coordinates of San Francisco
    )


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
        assert investor.rounds == [Round.get_by_id(1)]
        assert investor.industries == [Industry.get_by_id(1)]


def test_get_suggestions(populate_notable_investment, populate_investor, app):
    with app.app_context():
        sample_company = Company.get_by_id(1)

        investors = Investor.get_suggestions(sample_company, 7)

        assert investors is not None
        assert len(investors) == 7


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
        },
        {
            "id": 4,
            "first_name": "Holly",
            "last_name": "Rivera",
            "firm_name": "Horne and Sons",
            "about": "About Holly",
            "position": "Administrator, sports",
            "website": "https://www.byrd.info/mainterms.htm",
            "linkedin": "https://www.linkedin.com/in/Holly-Rivera",
            "twitter": "https://twitter.com/HollyRivera",
            "email": "4willistracey@example.net",
            "phone_number": "+12942155364",
            "n_investments": 111,
            "n_exits": 50,
            "min_investment": 35100000,
            "max_investment": 38900000,
            "location": "American Samoa",
            "coordinates": "-14.274,-170.7046",
            "country": "American Samoa",
            "bias": 43,
            "industries": ["Direct-to-Consumer (DTC)"],
            "rounds": ["Series B", "Series C"],
            "preferred_round": "Series C",
        },
        {
            "id": 5,
            "first_name": "Anthony",
            "last_name": "Foster",
            "firm_name": "Evans-Kelly",
            "about": "About Anthony",
            "position": "Occupational therapist",
            "website": "https://www.rogers.com/wp-content/categories/tagauthor.asp",
            "linkedin": "https://www.linkedin.com/in/Anthony-Foster",
            "twitter": "https://twitter.com/AnthonyFoster",
            "email": "5dominguezalan@example.com",
            "phone_number": "+18331440523",
            "n_investments": 195,
            "n_exits": 53,
            "min_investment": 43900000,
            "max_investment": 44800000,
            "location": "India",
            "coordinates": "14.92,78.9546",
            "country": "India",
            "bias": 60,
            "industries": ["Healthcare"],
            "rounds": ["Pre-seed", "Seed"],
            "preferred_round": "Seed",
        },
        {
            "id": 6,
            "first_name": "Emily",
            "last_name": "Smith",
            "firm_name": "Smith Ventures",
            "about": "About Emily",
            "position": "Managing Director",
            "website": "https://www.smithventures.com",
            "linkedin": "https://www.linkedin.com/in/emilysmith",
            "twitter": "https://twitter.com/emilysmith",
            "email": "emilysmith@example.com",
            "phone_number": "+12345678901",
            "n_investments": 75,
            "n_exits": 30,
            "min_investment": 50000,
            "max_investment": 3000000,
            "location": "Canada",
            "coordinates": "56.1304,-106.3468",
            "country": "Canada",
            "bias": 55,
            "industries": ["E-commerce", "SaaS"],
            "rounds": ["Seed", "Series A"],
            "preferred_round": "Seed",
        },
        {
            "id": 7,
            "first_name": "Michael",
            "last_name": "Johnson",
            "firm_name": "Johnson Capital",
            "about": "About Michael",
            "position": "Investment Analyst",
            "website": "https://www.johnsoncapital.com",
            "linkedin": "https://www.linkedin.com/in/michaeljohnson",
            "twitter": "https://twitter.com/michaeljohnson",
            "email": "michaeljohnson@example.com",
            "phone_number": "+19876543210",
            "n_investments": 50,
            "n_exits": 20,
            "min_investment": 200000,
            "max_investment": 10000000,
            "location": "United Kingdom",
            "coordinates": "55.3781,-3.436",
            "country": "United Kingdom",
            "bias": 48,
            "industries": ["Finance", "Real Estate"],
            "rounds": ["Series B", "Series C"],
            "preferred_round": "Series B",
        },
        {
            "id": 8,
            "first_name": "Jessica",
            "last_name": "Williams",
            "firm_name": "Williams Investments",
            "about": "About Jessica",
            "position": "Founder",
            "website": "https://www.williamsinvestments.com",
            "linkedin": "https://www.linkedin.com/in/jessicawilliams",
            "twitter": "https://twitter.com/jessicawilliams",
            "email": "jessicawilliams@example.com",
            "phone_number": "+15551234567",
            "n_investments": 90,
            "n_exits": 35,
            "min_investment": 100000,
            "max_investment": 5000000,
            "location": "Australia",
            "coordinates": "-25.2744,133.7751",
            "country": "Australia",
            "bias": 60,
            "industries": ["Healthtech", "Biotech"],
            "rounds": ["Seed", "Series A"],
            "preferred_round": "Seed",
        },
        {
            "id": 9,
            "first_name": "David",
            "last_name": "Martinez",
            "firm_name": "Martinez Capital",
            "about": "About David",
            "position": "Managing Partner",
            "website": "https://www.martinezcapital.com",
            "linkedin": "https://www.linkedin.com/in/davidmartinez",
            "twitter": "https://twitter.com/davidmartinez",
            "email": "davidmartinez@example.com",
            "phone_number": "+16667778888",
            "n_investments": 80,
            "n_exits": 25,
            "min_investment": 500000,
            "max_investment": 20000000,
            "location": "Mexico",
            "coordinates": "23.6345,-102.5528",
            "country": "Mexico",
            "bias": 45,
            "industries": ["Food & Beverage", "Retail"],
            "rounds": ["Series B", "Series C"],
            "preferred_round": "Series B",
        },
        {
            "id": 10,
            "first_name": "Sophia",
            "last_name": "Garcia",
            "firm_name": "Garcia Ventures",
            "about": "About Sophia",
            "position": "Managing Director",
            "website": "https://www.garciaventures.com",
            "linkedin": "https://www.linkedin.com/in/sophiagarcia",
            "twitter": "https://twitter.com/sophiagarcia",
            "email": "sophiagarcia@example.com",
            "phone_number": "+14445556666",
            "n_investments": 70,
            "n_exits": 28,
            "min_investment": 300000,
            "max_investment": 15000000,
            "location": "Brazil",
            "coordinates": "-14.235,-51.9253",
            "country": "Brazil",
            "bias": 52,
            "industries": ["Renewable Energy", "CleanTech"],
            "rounds": ["Seed", "Series A"],
            "preferred_round": "Seed",
        },
        {
            "id": 11,
            "first_name": "Daniel",
            "last_name": "Anderson",
            "firm_name": "Anderson Partners",
            "about": "About Daniel",
            "position": "Partner",
            "website": "https://www.andersonpartners.com",
            "linkedin": "https://www.linkedin.com/in/danielanderson",
            "twitter": "https://twitter.com/danielanderson",
            "email": "danielanderson@example.com",
            "phone_number": "+12223334444",
            "n_investments": 60,
            "n_exits": 22,
            "min_investment": 200000,
            "max_investment": 10000000,
            "location": "Germany",
            "coordinates": "51.1657,10.4515",
            "country": "Germany",
            "bias": 47,
            "industries": ["Automotive", "Manufacturing"],
            "rounds": ["Series B", "Series C"],
            "preferred_round": "Series B",
        },
        {
            "id": 12,
            "first_name": "Isabella",
            "last_name": "Lopez",
            "firm_name": "Lopez Ventures",
            "about": "About Isabella",
            "position": "Investment Associate",
            "website": "https://www.lopezventures.com",
            "linkedin": "https://www.linkedin.com/in/isabellalopez",
            "twitter": "https://twitter.com/isabellalopez",
            "email": "isabellalopez@example.com",
            "phone_number": "+17778889999",
            "n_investments": 55,
            "n_exits": 18,
            "min_investment": 100000,
            "max_investment": 5000000,
            "location": "France",
            "coordinates": "46.603354,1.888334",
            "country": "France",
            "bias": 50,
            "industries": ["Fashion", "Luxury Goods"],
            "rounds": ["Seed", "Series A"],
            "preferred_round": "Seed",
        },
        {
            "id": 13,
            "first_name": "Liam",
            "last_name": "Brown",
            "firm_name": "Brown Investments",
            "about": "About Liam",
            "position": "Investor Relations Manager",
            "website": "https://www.browninvestments.com",
            "linkedin": "https://www.linkedin.com/in/liambrown",
            "twitter": "https://twitter.com/liambrown",
            "email": "liambrown@example.com",
            "phone_number": "+18889997777",
            "n_investments": 70,
            "n_exits": 26,
            "min_investment": 300000,
            "max_investment": 15000000,
            "location": "South Africa",
            "coordinates": "-30.5595,22.9375",
            "country": "South Africa",
            "bias": 55,
            "industries": ["Mining", "Natural Resources"],
            "rounds": ["Series B", "Series C"],
            "preferred_round": "Series B",
        },
        {
            "id": 14,
            "first_name": "Olivia",
            "last_name": "Taylor",
            "firm_name": "Taylor Ventures",
            "about": "About Olivia",
            "position": "Managing Partner",
            "website": "https://www.taylorventures.com",
            "linkedin": "https://www.linkedin.com/in/oliviataylor",
            "twitter": "https://twitter.com/oliviataylor",
            "email": "oliviataylor@example.com",
            "phone_number": "+16668889999",
            "n_investments": 85,
            "n_exits": 32,
            "min_investment": 200000,
            "max_investment": 10000000,
            "location": "New Zealand",
            "coordinates": "-40.9006,174.886",
            "country": "New Zealand",
            "bias": 58,
            "industries": ["Tech", "Telecommunications"],
            "rounds": ["Seed", "Series A"],
            "preferred_round": "Seed",
        },
        {
            "id": 15,
            "first_name": "Noah",
            "last_name": "Wilson",
            "firm_name": "Wilson Capital",
            "about": "About Noah",
            "position": "Investment Analyst",
            "website": "https://www.wilsoncapital.com",
            "linkedin": "https://www.linkedin.com/in/noahwilson",
            "twitter": "https://twitter.com/noahwilson",
            "email": "noahwilson@example.com",
            "phone_number": "+14446667777",
            "n_investments": 60,
            "n_exits": 20,
            "min_investment": 100000,
            "max_investment": 5000000,
            "location": "Singapore",
            "coordinates": "1.3521,103.8198",
            "country": "Singapore",
            "bias": 52,
            "industries": ["Fintech", "Payments"],
            "rounds": ["Series B", "Series C"],
            "preferred_round": "Series B",
        },
        {
            "id": 16,
            "first_name": "William",
            "last_name": "Lee",
            "firm_name": "Lee Capital",
            "about": "About William",
            "position": "Senior Partner",
            "website": "https://www.leecapital.com",
            "linkedin": "https://www.linkedin.com/in/williamlee",
            "twitter": "https://twitter.com/williamlee",
            "email": "williamlee@example.com",
            "phone_number": "+15551234567",
            "n_investments": 70,
            "n_exits": 25,
            "min_investment": 500000,
            "max_investment": 15000000,
            "location": "Hong Kong",
            "coordinates": "22.3193,114.1694",
            "country": "Hong Kong",
            "bias": 55,
            "industries": ["Technology", "E-commerce"],
            "rounds": ["Seed", "Series A"],
            "preferred_round": "Series A",
        },
    ]
    return investor_list


@pytest.fixture()
def suggestion_builder_instance(suggestion_builder_data, sample_company):
    return SuggestionBuilder(investor_list=suggestion_builder_data, company=sample_company)


def test_suggestion_builder(suggestion_builder_instance):
    assert isinstance(suggestion_builder_instance, SuggestionBuilder)
    assert isinstance(suggestion_builder_instance.investor_list, list)
    assert len(suggestion_builder_instance.investor_list) == 16


def test_calculate_all_scores(suggestion_builder_instance):
    suggestion_builder_instance.calculate_all_scores()
    investors = suggestion_builder_instance.investor_list

    assert round(investors[13]["total_score"], 2) == 0.61
    assert round(investors[5]["total_score"], 2) == 0.5
    assert round(investors[0]["total_score"], 2) == 0.48
    assert round(investors[8]["total_score"], 2) == 0.41
    assert round(investors[9]["total_score"], 2) == 0.41


def test_sort_by_score(suggestion_builder_instance):
    suggestion_builder_instance.calculate_all_scores()
    suggestion_builder_instance.sort_by_score()
    investors = suggestion_builder_instance.investor_list

    assert investors[0]["id"] == 14
    assert investors[1]["id"] == 6
    assert investors[2]["id"] == 1
    assert investors[3]["id"] == 9
    assert investors[4]["id"] == 10


def test_get_id_list(suggestion_builder_data, sample_company):
    suggestion_builder = SuggestionBuilder(investor_list=suggestion_builder_data, company=sample_company)
    suggestion_builder.calculate_all_scores()
    id_list = suggestion_builder.get_id_list(quantity=5)

    assert len(id_list) == 5
