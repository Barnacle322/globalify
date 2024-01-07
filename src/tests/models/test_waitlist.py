import pytest

from ...project import db
from ...project.models import Waitlist, WaitlistCharge


@pytest.fixture()
def new_waitlist_charge(app):
    with app.app_context():
        waitlist_charge = WaitlistCharge(
            stripe_customer_id="stripe_id",
            charge_id="charge_id",
            customer_email="cus@example.com",
            customer_name="John Doe",
            random_key="12345",
            downloaded=False,
        )
        db.session.add(waitlist_charge)
        db.session.commit()


@pytest.fixture()
def new_waitlist(app):
    with app.app_context():
        waitlist = Waitlist(
            email="cus@example.com",
        )
        db.session.add(waitlist)
        db.session.commit()


def test_waitlist_charge(new_waitlist_charge, app):
    with app.app_context():
        waitlist_charge = WaitlistCharge.get_by_id(1)
        assert waitlist_charge
        waitlist_charge = WaitlistCharge.get_by_customer_id("stripe_id")
        assert waitlist_charge
        waitlist_charge = WaitlistCharge.get_by_charge_id("charge_id")
        assert waitlist_charge
        waitlist_charge = WaitlistCharge.get_by_random_key("12345")
        assert waitlist_charge
        waitlist_charge = WaitlistCharge.get_by_customer_email("cus@example.com")
        assert waitlist_charge
        assert waitlist_charge.stripe_customer_id == "stripe_id"
        assert waitlist_charge.charge_id == "charge_id"
        assert waitlist_charge.customer_email == "cus@example.com"
        assert waitlist_charge.customer_name == "John Doe"
        assert waitlist_charge.random_key == "12345"
        assert waitlist_charge.downloaded is False


def test_waitlist(new_waitlist, app):
    with app.app_context():
        waitlist = Waitlist.get_by_email("cus@example.com")
        assert waitlist
        assert waitlist.email == "cus@example.com"
