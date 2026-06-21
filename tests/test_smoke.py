def test_app_boots(app):
    assert app is not None
    assert app.testing is True


def test_expected_blueprints_registered(app):
    for name in ("auth", "main", "search", "settings", "profile", "admin"):
        assert name in app.blueprints


def test_app_handles_a_request(client):
    # an unknown path should still route through the app (proves it serves)
    response = client.get("/this-path-does-not-exist")
    assert response.status_code in (404, 308)
