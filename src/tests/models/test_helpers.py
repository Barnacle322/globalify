import pycountry

from src.project.models import Country, Industry, Round
from src.project.utils.info_lists import aggregate as industry_aggregate


def test_country(app):
    with app.app_context():
        country_list = []
        country_db_list = Country.get_all()

        for country in pycountry.countries:
            country_list.append((country.name, country.alpha_2))  # type: ignore

        assert len(country_db_list) == len(country_list)

        for i in range(len(country_db_list)):
            assert country_db_list[i].name == country_list[i][0]
            assert country_db_list[i].code == country_list[i][1]


def test_country_get_by_id(app):
    with app.app_context():
        country = Country.get_by_id(1)
        assert country
        assert country.name == "Aruba"
        assert country.code == "AW"


def test_country_get_by_code(app):
    with app.app_context():
        country = Country.get_by_code("KG")
        assert country
        assert country.name == "Kyrgyzstan"
        assert country.code == "KG"


def test_country_get_by_name(app):
    with app.app_context():
        country = Country.get_by_name("United States")
        assert country
        assert country.name == "United States"
        assert country.code == "US"


def test_country_get_by_name_not_existing(app):
    with app.app_context():
        country = Country.get_by_name("Narnia")
        assert country is None


def test_industry(app):
    with app.app_context():
        industry_list = []
        industry_db_list = Industry.get_industry_list()

        for sublist in industry_aggregate.values():
            industry_list += sublist
        assert industry_db_list
        assert len(industry_db_list) == len(industry_list)

        for i in range(len(industry_db_list)):
            assert industry_db_list[i].name in industry_list


def test_industry_get_by_id(app):
    with app.app_context():
        industry = Industry.get_by_id(1)
        assert industry
        assert industry.name == "AI"


def test_industry_get_by_name(app):
    with app.app_context():
        industry = Industry.get_by_name("AI")
        assert industry
        assert industry.name == "AI"


def test_industry_get_by_name_not_existing(app):
    with app.app_context():
        industry = Industry.get_by_name("Search Engine")
        assert industry is None


def test_round(app):
    with app.app_context():
        round_list = ["Pre-Seed", "Seed", "Series A", "Series B", "Series C"]
        round_db_list = Round.get_all()
        assert len(round_db_list) == len(round_list)

        for item in round_db_list:
            assert item.name in round_list


def test_round_get_by_id(app):
    with app.app_context():
        round = Round.get_by_id(1)
        assert round
        assert round.name == "Pre-Seed"


def test_round_get_by_name(app):
    with app.app_context():
        round = Round.get_by_name("Pre-Seed")
        assert round
        assert round.name == "Pre-Seed"


def test_round_get_by_name_not_existing(app):
    with app.app_context():
        round = Round.get_by_name("Series D")
        assert round is None
