def test_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Globalify is" in response.data
    assert b"Tailored experience for specific regions" in response.data
    assert b"Frequently asked questions" in response.data
    assert b"From the blog" in response.data
    assert b"Use Globalify - Fund Your Startup" in response.data


def test_waitlist(client):
    response = client.get("/waitlist")
    assert response.status_code == 200
    assert b"Limited time offer!" in response.data
    assert b"Frequently asked questions" in response.data
    assert b"Use Globalify - Fund Your Startup" in response.data


def test_about(client):
    response = client.get("/about")
    assert response.status_code == 200
    assert b"mission and vision" in response.data
    assert b"Our Passion" in response.data
    assert b"Our platform" in response.data
    assert b"The what, the how, the who" in response.data
    assert b"The team" in response.data
    assert b"info@globalify.xyz" in response.data
    assert b"Use Globalify - Fund Your Startup" in response.data
