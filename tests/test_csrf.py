import re

import pytest

from app import create_app, db


@pytest.fixture
def csrf_client():
    app = create_app({
        "TESTING": True,
        "SECRET_KEY": "csrf-test-secret",
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": True,
    })

    with app.app_context():
        db.create_all()

    yield app.test_client()

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_post_without_csrf_token_is_rejected(csrf_client):
    response = csrf_client.post("/login", data={
        "email": "user@test.com",
        "password": "secret123",
    })

    assert response.status_code == 400


def test_post_with_valid_csrf_token_is_accepted(csrf_client):
    page = csrf_client.get("/login")
    assert page.status_code == 200

    match = re.search(
        rb'name="csrf_token"\s+value="([^"]+)"',
        page.data,
    )
    assert match is not None

    token = match.group(1).decode()

    response = csrf_client.post("/login", data={
        "csrf_token": token,
        "email": "unknown@test.com",
        "password": "wrongpassword",
    })

    assert response.status_code == 200