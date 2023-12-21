import pycountry

from ...project.models import Country, Industry, Round
from ...project.utils.info_lists import aggregate as industry_aggregate


def test_country_database(app):
    with app.app_context():
        country_list = []
        for country in pycountry.countries:
            country_list.append((country.name, country.alpha_2)) # type: ignore

        assert Country.query.count() == len(pycountry.countries)

        for i in range(Country.query.count()):
            country_obj = Country.get_by_id(id=i + 1)

            assert country_obj
            assert country_obj.name == country_list[i][0]
            assert country_obj.code == country_list[i][1]


def test_industry_database(app):
    with app.app_context():
        industry_list = []
        for sublist in industry_aggregate.values():
            industry_list += sublist

        assert Industry.query.count() == len(industry_list)

        for i in range(1, Industry.query.count() + 1):
            industry_obj = Industry.get_by_id(i)

            assert industry_obj
            assert industry_obj.name in industry_aggregate.get(industry_obj.category, [])


def test_round_database(app):
    with app.app_context():
        round_list = ["Pre-Seed", "Seed", "Series A", "Series B", "Series C"]

        assert Round.query.count() == len(round_list)

        for item in Round.query.all():
            assert item.name in round_list
