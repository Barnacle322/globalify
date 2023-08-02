import pytest

from ...project import db
from ...project.models import User, UserInfo

# from ..conftest import client, app


@pytest.fixture(scope="module")
def new_user():
    user = User(email="testuser@example.com")  # type: ignore
    user.password = "testpassword"
    return user


@pytest.fixture(scope="module")
def new_user_info(new_user):
    user_info = UserInfo(
        user_id=new_user.id,
        user=new_user,
        username="testusername",
        first_name="testfirstname",
        last_name="testlastname",
        linkedin="testlinkedin",
        instagram="testinstagram",
        bio="testbio",
    )
    return user_info


@pytest.fixture(scope="module")
def full_user():
    full_user = (
        1,
        "testuser@example.com",
        "testusername",
        "testfirstname",
        "testlastname",
        "testlinkedin",
        "testinstagram",
        "testbio",
        False,
    )
    return full_user


def test_new_user(new_user, app):
    with app.app_context():
        db.session.add(new_user)
        db.session.commit()
        assert new_user.id == 1


def test_get_user_by_id(new_user, app):
    with app.app_context():
        db.session.add(new_user)
        db.session.commit()
        user = User.get_by_id(1)
        assert user == new_user


def test_get_user_by_email(new_user, app):
    with app.app_context():
        db.session.add(new_user)
        db.session.commit()
        user = User.get_by_email("testuser@example.com")
        assert user == new_user


def test_signed_with_oauth(new_user, app):
    with app.app_context():
        db.session.add(new_user)
        db.session.commit()
        signed_with_oauth = User.signed_with_oauth("testuser@example.com")
        assert not signed_with_oauth


def test_new_user_info(new_user_info, app):
    with app.app_context():
        db.session.add(new_user_info)
        db.session.commit()
        assert new_user_info.id == 1
        assert new_user_info.user_id == 1


def test_get_user_info_by_user_id(new_user_info, app, full_user):
    with app.app_context():
        db.session.add(new_user_info)
        db.session.commit()
        user_info = UserInfo.get_by_user_id(1)
        assert user_info == full_user


def test_get_user_info_by_username(new_user_info, app, full_user):
    with app.app_context():
        db.session.add(new_user_info)
        db.session.commit()
        user_info = UserInfo.get_by_username("testusername")
        assert user_info == full_user
