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


def test_waitlist_apply(client):
    response = client.get("/waitlist/apply")
    assert response.status_code == 200
    assert b"Join Globalify!" in response.data
    assert b"Email" in response.data
    assert b"First name" in response.data
    assert b"Last name" in response.data
    assert b"Proceed" in response.data


def test_waitlist_email(client):
    response = client.post(
        "/waitlist-email", json=dict(email="johndoe@example.com"), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert b"Email added." in response.data


def test_waitlist_email_empty(client):
    response = client.post("/waitlist-email", json=dict(email=""), headers={"Content-Type": "application/json"})
    assert response.status_code == 200
    assert b"Please enter an email." in response.data


def test_waitlist_email_invalid(client):
    response = client.post(
        "/waitlist-email", json=dict(email="invalid_email"), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert b"Please enter a valid email." in response.data


def test_waitlist_email_duplicate(client):
    client.post("/waitlist-email", json=dict(email="johndoe@example.com"), headers={"Content-Type": "application/json"})
    response = client.post(
        "/waitlist-email", json=dict(email="johndoe@example.com"), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 200
    assert b"Email is already in the system." in response.data


def test_waitlist_cancel(client):
    response = client.get("/waitlist/cancel")
    assert response.status_code == 200
    assert b"Payment canceled" in response.data
    assert b"You have not been charged." in response.data
    assert b"Go to home" in response.data


def test_waitlist_success(client):
    response = client.get("/waitlist/success")
    assert response.status_code == 200
    assert b"Thank you!" in response.data
    assert b"Thank you for your purchase!" in response.data
    assert b"Home" in response.data


def test_download_refused(client):
    response = client.get("/download/random_key")
    assert response.status_code == 200
    assert b"Huh! It looks like you may have already downloaded our list of investors." in response.data
    assert b"Please check your downloads folder." in response.data
