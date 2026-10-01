"""Integration tests: routes + database + session."""
from app import db
from app.models import User
from tests.conftest import login


def register(client, name="Ann", email="ann@test.com", password="secret123"):
    return client.post("/register", data={"name": name, "email": email, "password": password},
                       follow_redirects=True)


def test_register_success(client, app):
    """TC-Reg-01"""
    r = register(client)
    assert b"Registration successful" in r.data
    with app.app_context():
        u = User.query.filter_by(email="ann@test.com").first()
        assert u is not None and u.password_hash != "secret123"


def test_register_duplicate_email(client, app):
    """TC-Reg-02"""
    register(client)
    r = register(client, name="Other")
    assert b"Email already registered" in r.data
    with app.app_context():
        assert User.query.filter_by(email="ann@test.com").count() == 1


def test_register_duplicate_email_case_insensitive(client):
    """TC-Reg-02 (boundary)"""
    register(client)
    r = register(client, email="ANN@TEST.COM")
    assert b"Email already registered" in r.data


def test_register_invalid_inputs(client, app):
    """TC-Reg-01 error cases / TC-Sec-04"""
    assert b"valid email" in register(client, email="bad").data
    assert b"at least 6" in register(client, password="123").data
    assert b"Name is required" in register(client, name="  ").data
    with app.app_context():
        assert User.query.count() == 0


def test_register_script_input_is_escaped(client):
    """TC-Sec-04: XSS attempt is escaped on display."""
    register(client, name="<script>alert(1)</script>")
    login(client, "ann@test.com")
    r = client.get("/")
    assert b"<script>alert(1)</script>" not in r.data


def test_login_success_reaches_dashboard(client, make_user):
    """TC-Auth-02"""
    make_user()
    r = login(client)
    assert b"Parking Slots" in r.data


def test_login_wrong_password(client, make_user):
    """TC-Auth-02 error case"""
    make_user()
    r = login(client, password="nope")
    assert b"Invalid email or password" in r.data


def test_login_unknown_user(client):
    r = login(client, "ghost@test.com")
    assert b"Invalid email or password" in r.data


def test_dashboard_requires_login(client):
    """TC-Sec-01"""
    r = client.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_logout_invalidates_session(user_client):
    """TC-Sec-01 / VPS-SR-003"""
    assert user_client.get("/").status_code == 200
    user_client.get("/logout")
    r = user_client.get("/")
    assert r.status_code == 302 and "/login" in r.headers["Location"]
    assert user_client.get("/history").status_code == 302
