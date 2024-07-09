import pytest

from ...project import db
from ...project.models import Industry, Investor, NotableInvestment, Round


@pytest.fixture()
def new_investors(app):
    with app.app_context():
        notable_investment1 = NotableInvestment(name="Notable Investment 1")
        notable_investment2 = NotableInvestment(name="Notable Investment 2")
        db.session.add_all([notable_investment1, notable_investment2])
        db.session.commit()

        investor1 = Investor(
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
            # location="Chad",
            # _coordinates="20.45,16.5167",
            # _country="Chad",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment1, notable_investment2],
        )

        investor2 = Investor(
            first_name="Sophia",
            last_name="Garcia",
            firm_name="Garcia Ventures",
            about="About Sophia",
            position="Managing Director",
            website="https://www.garciaventures.com",
            linkedin="https://www.linkedin.com/in/sophiagarcia",
            twitter="https://twitter.com/sophiagarcia",
            email="sophiagarcia@example.com",
            phone_number="+14445556666",
            n_investments=70,
            n_exits=28,
            min_investment=300000,
            max_investment=15000000,
            # location="Brazil",
            # _coordinates="-14.235,-51.9253",
            # _country="Brazil",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment1, notable_investment2],
        )

        investor3 = Investor(
            first_name="Bob",
            last_name="Doe",
            firm_name="Apple",
            about="About Bob",
            position="CTO",
            website="https://www.apple.com",
            linkedin="https://www.linkedin.com/in/Bob",
            twitter="https://www.twitter.com/bob",
            email="bobdoe@example.com",
            phone_number="+11806123574",
            n_investments=86,
            n_exits=25,
            min_investment=300000,
            max_investment=90000000,
            # location="Nepal",
            # _coordinates="29.25,82.2167",
            # _country="Nepal",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment1, notable_investment2],
        )

        investor4 = Investor(
            first_name="Holly",
            last_name="Rivera",
            firm_name="Horne and Sons",
            about="About Holly",
            position="Administrator, sports",
            website="https://www.byrd.info/mainterms.htm",
            linkedin="https://www.linkedin.com/in/Holly-Rivera",
            twitter="https://twitter.com/HollyRivera",
            email="4willistracey@example.net",
            phone_number="+12942155364",
            n_investments=111,
            n_exits=50,
            min_investment=35100000,
            max_investment=38900000,
            # location="American Samoa",
            # _coordinates="-14.274,-170.7046",
            # _country="American Samoa",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment1, notable_investment2],
        )

        investor5 = Investor(
            first_name="Anthony",
            last_name="Foster",
            firm_name="Evans-Kelly",
            about="About Anthony",
            position="Occupational therapist",
            website="https://www.rogers.com/wp-content/categories/tagauthor.asp",
            linkedin="https://www.linkedin.com/in/Anthony-Foster",
            twitter="https://twitter.com/AnthonyFoster",
            email="5dominguezalan@example.com",
            phone_number="+18331440523",
            n_investments=195,
            n_exits=53,
            min_investment=43900000,
            max_investment=44800000,
            # location="India",
            # _coordinates="14.92,78.9546",
            # _country="India",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment1, notable_investment2],
        )

        investor6 = Investor(
            first_name="Emily",
            last_name="Smith",
            firm_name="Smith Ventures",
            about="About Emily",
            position="Managing Director",
            website="https://www.smithventures.com",
            linkedin="https://www.linkedin.com/in/emilysmith",
            twitter="https://twitter.com/emilysmith",
            email="emilysmith@example.com",
            phone_number="+12345678901",
            n_investments=75,
            n_exits=30,
            min_investment=50000,
            max_investment=3000000,
            # location="Canada",
            # _coordinates="56.1304,-106.3468",
            # _country="Canada",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment1, notable_investment2],
        )

        investor7 = Investor(
            first_name="Michael",
            last_name="Johnson",
            firm_name="Johnson Capital",
            about="About Michael",
            position="Investment Analyst",
            website="https://www.johnsoncapital.com",
            linkedin="https://www.linkedin.com/in/michaeljohnson",
            twitter="https://twitter.com/michaeljohnson",
            email="michaeljohnson@example.com",
            phone_number="+19876543210",
            n_investments=50,
            n_exits=20,
            min_investment=200000,
            max_investment=10000000,
            # location="United Kingdom",
            # _coordinates="55.3781,-3.436",
            # _country="United Kingdom",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment1, notable_investment2],
        )

        investor8 = Investor(
            first_name="Jessica",
            last_name="Williams",
            firm_name="Williams Investments",
            about="About Jessica",
            position="Founder",
            website="https://www.williamsinvestments.com",
            linkedin="https://www.linkedin.com/in/jessicawilliams",
            twitter="https://twitter.com/jessicawilliams",
            email="jessicawilliams@example.com",
            phone_number="+15551234567",
            n_investments=90,
            n_exits=35,
            min_investment=100000,
            max_investment=5000000,
            # location="Australia",
            # _coordinates="-25.2744,133.7751",
            # _country="Australia",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment1, notable_investment2],
        )

        investor9 = Investor(
            first_name="David",
            last_name="Martinez",
            firm_name="Martinez Capital",
            about="About David",
            position="Managing Partner",
            website="https://www.martinezcapital.com",
            linkedin="https://www.linkedin.com/in/davidmartinez",
            twitter="https://twitter.com/davidmartinez",
            email="davidmartinez@example.com",
            phone_number="+16667778888",
            n_investments=80,
            n_exits=25,
            min_investment=500000,
            max_investment=20000000,
            # location="Mexico",
            # _coordinates="23.6345,-102.5528",
            # _country="Mexico",
            rounds=[Round.get_by_id(1)],
            industries=[Industry.get_by_id(1)],
            notable_investments=[notable_investment1, notable_investment2],
        )

        db.session.add_all(
            [investor1, investor2, investor3, investor4, investor5, investor6, investor7, investor8, investor9]
        )
        db.session.commit()

        investor1.set_slug()


@pytest.fixture()
def new_notable_investment(app):
    with app.app_context():
        notable_investment1 = NotableInvestment(name="Notable Investment 1")
        notable_investment2 = NotableInvestment(name="Notable Investment 2")
        db.session.add_all([notable_investment1, notable_investment2])
        db.session.commit()


def test_investor(new_investors, app):
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
        # assert investor.location == "Chad"
        # assert investor._coordinates == "20.45,16.5167"
        # assert investor._country == "Chad"
        assert investor.rounds == [Round.get_by_id(1)]
        assert investor.industries == [Industry.get_by_id(1)]
        assert investor.notable_investments == [
            NotableInvestment.get_by_name("Notable Investment 1"),
            NotableInvestment.get_by_name("Notable Investment 2"),
        ]


def test_get_all(new_investors, app):
    with app.app_context():
        investors = Investor.get_all()
        assert investors
        assert len(investors) == 9

        assert investors[0].id == 1
        assert investors[1].id == 2
        assert investors[2].id == 3
        assert investors[3].id == 4
        assert investors[4].id == 5
        assert investors[5].id == 6
        assert investors[6].id == 7
        assert investors[7].id == 8
        assert investors[8].id == 9


def test_get_by_email_existing(new_investors, app):
    with app.app_context():
        investor = Investor.get_by_email("jane@example.com")
        assert investor
        assert investor.email == "jane@example.com"


def test_get_by_email_not_existing(app):
    with app.app_context():
        investor = Investor.get_by_email("johndoe@example.com")
        assert not investor


def test_get_by_id_existing(new_investors, app):
    with app.app_context():
        investor = Investor.get_by_id(1)
        assert investor
        assert investor.id == 1


def test_get_by_id_non_existing(new_investors, app):
    with app.app_context():
        investor = Investor.get_by_id(999)
        assert investor is None


def test_get_by_id_list_existing(new_investors, app):
    with app.app_context():
        investor_ids = [1, 2, 3]
        investors = Investor.get_by_id_list(investor_ids)
        assert investors
        assert len(investors) == 3
        assert investors[0].id == 1
        assert investors[1].id == 2
        assert investors[2].id == 3


def test_get_by_id_list_non_existing(new_investors, app):
    with app.app_context():
        investor_ids = [999, 123, 451]
        investors = Investor.get_by_id_list(investor_ids)
        assert investors == []


def test_get_all_notable_investments(new_notable_investment, app):
    with app.app_context():
        notable_investments = NotableInvestment.get_all()
        assert notable_investments
        assert len(notable_investments) == 2
        assert notable_investments[0].name == "Notable Investment 1"
        assert notable_investments[1].name == "Notable Investment 2"


def test_get_by_id_existing_notable_investment(new_notable_investment, app):
    with app.app_context():
        notable_investment = NotableInvestment.get_by_id(1)
        assert notable_investment
        assert notable_investment.id == 1
        assert notable_investment.name == "Notable Investment 1"


def test_get_by_id_non_existing_notable_investment(new_notable_investment, app):
    with app.app_context():
        notable_investment = NotableInvestment.get_by_id(999)
        assert notable_investment is None


def test_get_by_name_existing_notable_investment(new_notable_investment, app):
    with app.app_context():
        notable_investment = NotableInvestment.get_by_name("Notable Investment 1")
        assert notable_investment
        assert notable_investment.name == "Notable Investment 1"


def test_get_by_name_non_existing_notable_investment(new_notable_investment, app):
    with app.app_context():
        notable_investment = NotableInvestment.get_by_name("Nonexistent Investment")
        assert notable_investment is None


# TODO
# def test_get_by_slug_existing(new_investors, app):
#     with app.app_context():
#         investor = Investor.query.first()
#         print(investor)
#         investor = Investor.get_by_slug("JaneDoe")
#         print(investor)
#         investors = Investor.get_all()
#         print(investors[1].slug)
#         assert investor
#         assert investor.slug == "jane-doe"


# def test_get_by_slug_not_existing(app):
#     with app.app_context():
#         investor = Investor.get_by_slug("industy-example")
#         assert not investor
