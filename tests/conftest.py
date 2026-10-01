import pytest

from app import create_app, db
from app.models import ParkingSlot, User


@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_user(app):
    def _make(email="user@test.com", password="secret123", role="customer", name="Test"):
        with app.app_context():
            u = User(name=name, email=email, role=role)
            u.set_password(password)
            db.session.add(u)
            db.session.commit()
            return u.id
    return _make


@pytest.fixture
def make_slot(app):
    def _make(number="A-01", floor=1, status="available"):
        with app.app_context():
            s = ParkingSlot(slot_number=number, floor=floor, status=status)
            db.session.add(s)
            db.session.commit()
            return s.id
    return _make


def login(client, email="user@test.com", password="secret123"):
    return client.post("/login", data={"email": email, "password": password},
                       follow_redirects=True)


@pytest.fixture
def user_client(client, make_user):
    make_user()
    login(client)
    return client


@pytest.fixture
def admin_client(app, make_user):
    make_user(email="admin@test.com", role="admin", name="Admin")
    c = app.test_client()
    login(c, "admin@test.com")
    return c
