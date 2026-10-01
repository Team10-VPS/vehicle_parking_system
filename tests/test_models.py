"""Unit tests for models and validators."""
import pytest
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import ParkingSlot, User
from app.utils import valid_email, valid_plate


def test_password_is_hashed_not_plain(app):
    """TC-Auth-01 / TC-Sec-02: password stored as a hash."""
    u = User(name="A", email="a@b.com")
    u.set_password("secret123")
    assert u.password_hash != "secret123"
    assert "secret123" not in u.password_hash


def test_check_password_correct_and_wrong(app):
    """TC-Auth-02: verification succeeds only for the right password."""
    u = User(name="A", email="a@b.com")
    u.set_password("secret123")
    assert u.check_password("secret123")
    assert not u.check_password("wrong")
    assert not u.check_password("")


def test_same_password_gives_different_hashes(app):
    """TC-Sec-02: salted hashing."""
    a, b = User(name="a", email="a@x.com"), User(name="b", email="b@x.com")
    a.set_password("samepass1")
    b.set_password("samepass1")
    assert a.password_hash != b.password_hash


def test_duplicate_email_rejected_by_db(app):
    """TC-Reg-02: unique email constraint."""
    with app.app_context():
        db.session.add(User(name="A", email="a@b.com", password_hash="x"))
        db.session.commit()
        db.session.add(User(name="B", email="a@b.com", password_hash="y"))
        with pytest.raises(IntegrityError):
            db.session.commit()


def test_default_role_is_customer(app):
    assert User(name="A", email="a@b.com").is_admin is False
    assert User(name="A", email="a@b.com", role="admin").is_admin is True


def test_slot_defaults_to_available(app):
    """TC-Slot-01"""
    with app.app_context():
        s = ParkingSlot(slot_number="A-01", floor=1)
        db.session.add(s)
        db.session.commit()
        assert s.status == "available"


def test_duplicate_slot_number_rejected(app):
    """TC-Admin-01 (boundary)"""
    with app.app_context():
        db.session.add(ParkingSlot(slot_number="A-01", floor=1))
        db.session.commit()
        db.session.add(ParkingSlot(slot_number="A-01", floor=2))
        with pytest.raises(IntegrityError):
            db.session.commit()


@pytest.mark.parametrize("email,ok", [
    ("a@b.com", True), ("first.last@mail.co.in", True),
    ("", False), ("no-at-sign", False), ("a@b", False), ("a b@c.com", False),
])
def test_valid_email(email, ok):
    """TC-Sec-04: input validation."""
    assert valid_email(email) is ok


@pytest.mark.parametrize("plate,ok", [
    ("KA01AB1234", True), ("TN-09 X 1", True),
    ("", False), ("AB", False), ("<script>", False), ("A" * 16, False),
])
def test_valid_plate(plate, ok):
    """TC-Sec-04 / TC-Book-02 (boundary lengths)"""
    assert valid_plate(plate) is ok
