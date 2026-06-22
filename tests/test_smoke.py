import pytest
from pydantic import ValidationError


def test_app_boots(app):
    assert app is not None
    assert app.testing is True


def test_expected_blueprints_registered(app):
    for name in ("auth", "main", "search", "settings", "admin"):
        assert name in app.blueprints


def test_app_handles_a_request(client):
    # an unknown path should still route through the app (proves it serves)
    response = client.get("/this-path-does-not-exist")
    assert response.status_code in (404, 308)


def test_create_app_requires_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    import sys

    sys.modules.pop("project", None)

    with pytest.raises(ValidationError):
        from project import create_app  # noqa: F401


def test_db_metadata_creates_all_tables(app):
    from project.extensions import db

    with app.app_context():
        db.create_all()  # raises NoReferencedTableError if any FK points at a deleted table


def test_no_url_for_to_unregistered_endpoints(app):
    import re
    from pathlib import Path

    registered = {rule.endpoint for rule in app.url_map.iter_rules()}
    pattern = re.compile(r'url_for\(\s*["\']([a-zA-Z_][\w.]*)["\']')
    offenders = []
    for py in Path("src/project").rglob("*.py"):
        for endpoint in pattern.findall(py.read_text()):
            if endpoint not in registered:
                offenders.append(f"{py}: {endpoint}")
    assert not offenders, "url_for to unregistered endpoints:\n" + "\n".join(offenders)
