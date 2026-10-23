import pytest
from sqlalchemy import select
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash
from app import create_app
from app.cli import _bootstrap
from app.extensions import db
from app.models import Role, User


@pytest.fixture()
def app():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "TESTING": True, "SECRET_KEY": "test",
                      "SQLALCHEMY_ENGINE_OPTIONS": {"poolclass": StaticPool, "connect_args": {"check_same_thread": False}}})
    with app.app_context():
        db.create_all()
        _bootstrap()
        for username, name, role in (("admin", "Admin", "ADMIN"), ("awa", "Awa", "EMPLOYE"), ("fatou", "Fatou", "EMPLOYE")):
            r = db.session.execute(select(Role).where(Role.name == role)).scalar_one()
            db.session.add(User(username=username, full_name=name, role=r, password_hash=generate_password_hash("motdepasse1")))
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def auth(client, username):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": "motdepasse1"})
    assert r.status_code == 200, r.get_json()
    return {"Authorization": "Bearer " + r.get_json()["token"]}


@pytest.fixture()
def admin(client):
    return auth(client, "admin")


@pytest.fixture()
def awa(client):
    return auth(client, "awa")


@pytest.fixture()
def fatou(client):
    return auth(client, "fatou")


@pytest.fixture()
def product(client, admin):
    r = client.post("/api/v1/products", headers=admin, json={"name": "Voile noir Premium", "purchase_price": 3000,
                                                             "sell_price": 5000, "initial_qty": 10, "alert_threshold": 3})
    assert r.status_code == 201, r.get_json()
    return r.get_json()
