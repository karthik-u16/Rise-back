from datetime import date, timedelta

import pytest

from app import WaterTracker, app, db


@pytest.fixture()
def client():
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client


def register_and_login(client):
    client.post("/register", data={"username": "warrior", "password": "strong-pass"})
    return client.post(
        "/login",
        data={"username": "warrior", "password": "strong-pass"},
        follow_redirects=True,
    )


def test_healthcheck(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert response.location.endswith("/login")


def test_register_login_and_dashboard_render(client):
    response = register_and_login(client)
    assert response.status_code == 200
    assert b"WORLD TO TRANSFORM YOU" in response.data


def test_state_changes_reject_get(client):
    register_and_login(client)
    for path in ("/complete/1", "/add-water/250", "/boss-battle", "/shadow-boss", "/logout"):
        assert client.get(path).status_code == 405


def test_water_is_scoped_to_current_day(client):
    register_and_login(client)
    client.post("/add-water/250")
    with app.app_context():
        rows = WaterTracker.query.order_by(WaterTracker.water_date).all()
        assert len(rows) == 1
        assert rows[0].water_ml == 250
        rows[0].water_date = date.today() - timedelta(days=1)
        db.session.commit()

    client.get("/dashboard")
    with app.app_context():
        today = WaterTracker.query.filter_by(water_date=date.today()).one()
        assert today.water_ml == 0
