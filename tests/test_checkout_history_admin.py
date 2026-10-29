"""Check-out, history and admin integration tests."""

import logging

from app import db
from app.models import Booking, ParkingSlot
from tests.conftest import login


def book(client, sid, plate="KA01AB1234"):
    return client.post("/book", data={
        "slot_id": sid, "vehicle_number": plate, "vehicle_type": "car"
    }, follow_redirects=True)


def test_customer_checkout(user_client, make_slot, app):
    """TC-Checkout-01"""
    sid = make_slot()
    book(user_client, sid)
    r = user_client.post("/checkout/1", follow_redirects=True)
    assert b"Checked out successfully" in r.data
    with app.app_context():
        b = db.session.get(Booking, 1)
        assert b.status == "completed" and b.check_out is not None
        assert db.session.get(ParkingSlot, sid).status == "available"


def test_double_checkout_returns_409(user_client, make_slot):
    """TC-Checkout-01 boundary: completed booking returns HTTP 409."""
    book(user_client, make_slot())
    first_response = user_client.post("/checkout/1")
    assert first_response.status_code == 302

    second_response = user_client.post("/checkout/1")
    assert second_response.status_code == 409
    assert b"already completed" in second_response.data

def test_other_customer_cannot_checkout(app, user_client, make_slot, make_user):
    """TC-Checkout-02 / VPS-SR-005"""
    book(user_client, make_slot())
    make_user(email="eve@test.com")
    eve = app.test_client()
    login(eve, "eve@test.com")
    assert eve.post("/checkout/1").status_code == 403
    with app.app_context():
        assert db.session.get(Booking, 1).status == "active"


def test_checkout_unknown_booking(user_client):
    assert user_client.post("/checkout/999").status_code == 404


def test_history_shows_own_bookings_only(app, user_client, make_slot, make_user):
    """TC-Hist-01"""
    book(user_client, make_slot("A-01"), "AAA111")
    make_user(email="bob@test.com")
    bob = app.test_client()
    login(bob, "bob@test.com")
    book(bob, make_slot("A-02"), "BBB222")
    mine = user_client.get("/history").data
    assert b"AAA111" in mine and b"BBB222" not in mine


def test_history_empty(user_client):
    assert b"No bookings yet" in user_client.get("/history").data


def test_completed_booking_remains_in_history(user_client, make_slot):
    """Completed bookings remain visible after checkout."""
    slot_id = make_slot("A-01")
    book(user_client, slot_id, "AAA111")

    response = user_client.post("/checkout/1", follow_redirects=True)

    assert response.status_code == 200
    assert b"My Booking History" in response.data
    assert b"A-01" in response.data
    assert b"AAA111" in response.data
    assert b"completed" in response.data
    assert b"Check-out" in response.data


def test_history_requires_login(client):
    """Unauthenticated users are redirected to login."""
    response = client.get("/history")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]



def test_admin_add_slot(admin_client, app):
    """TC-Admin-01"""
    r = admin_client.post("/admin/slots", data={"slot_number": "z-9", "floor": "4"},
                          follow_redirects=True)
    assert b"added" in r.data
    with app.app_context():
        assert ParkingSlot.query.filter_by(slot_number="Z-9", floor=4).count() == 1


def test_admin_add_slot_validation(admin_client, make_slot):
    """TC-Admin-01 error cases"""
    make_slot("A-01")
    assert b"already exists" in admin_client.post(
        "/admin/slots", data={"slot_number": "a-01", "floor": "1"}).data
    assert b"Floor must be" in admin_client.post(
        "/admin/slots", data={"slot_number": "Q1", "floor": "abc"}).data
    assert b"Slot number is required" in admin_client.post(
        "/admin/slots", data={"slot_number": "", "floor": "1"}).data


def test_admin_remove_available_slot(admin_client, make_slot, app):
    """TC-Admin-02"""
    sid = make_slot()
    admin_client.post(f"/admin/slots/{sid}/delete")
    with app.app_context():
        assert db.session.get(ParkingSlot, sid) is None


def test_admin_cannot_remove_occupied_slot(admin_client, make_slot, app):
    """TC-Admin-02 error"""
    sid = make_slot(status="occupied")
    r = admin_client.post(f"/admin/slots/{sid}/delete", follow_redirects=True)
    assert b"Cannot remove" in r.data
    with app.app_context():
        assert db.session.get(ParkingSlot, sid) is not None


def test_admin_view_and_force_checkout(app, admin_client, user_client, make_slot):
    """TC-Admin-03"""
    sid = make_slot()
    book(user_client, sid)
    assert b"user@test.com" in admin_client.get("/admin/bookings").data
    admin_client.post("/admin/checkout/1")
    with app.app_context():
        assert db.session.get(Booking, 1).status == "completed"
        assert db.session.get(ParkingSlot, sid).status == "available"


def test_non_admin_blocked_from_admin_routes(user_client):
    """TC-Sec-03 / VPS-SR-002"""
    assert user_client.get("/admin/slots").status_code == 403
    assert user_client.get("/admin/bookings").status_code == 403
    assert user_client.post("/admin/slots", data={"slot_number": "X", "floor": "1"}).status_code == 403
    assert user_client.post("/admin/checkout/1").status_code == 403


def test_anonymous_blocked_from_admin_routes(client):
    """TC-Sec-03"""
    assert client.get("/admin/slots").status_code == 302


def test_slot_status_consistent_with_bookings(user_client, make_slot, app):
    """TC-Rel-01: occupied slots == active bookings through book/checkout cycle"""
    ids = [make_slot(f"A-0{i}") for i in range(1, 4)]
    for i, sid in enumerate(ids):
        book(user_client, sid, f"PLT{i}00")
    user_client.post("/checkout/2")
    with app.app_context():
        occupied = ParkingSlot.query.filter_by(status="occupied").count()
        active = Booking.query.filter_by(status="active").count()
        assert occupied == active == 2


def test_history_checkout_has_confirmation_prompt(user_client, make_slot):
    """Checkout button asks for confirmation before submitting."""
    book(user_client, make_slot())
    response = user_client.get("/history")

    assert response.status_code == 200
    assert b"onsubmit" in response.data
    assert b"Are you sure you want to check out this booking?" in response.data


def test_checkout_commit_failure_rolls_back(
    app, user_client, make_slot, monkeypatch
):
    """A failed checkout commit must leave booking and slot unchanged."""
    slot_id = make_slot()
    book(user_client, slot_id)

    with app.app_context():
        booking = Booking.query.first()
        booking_id = booking.id
        original_status = booking.status
        original_slot_status = booking.slot.status
        session_class = type(db.session())

    def fail_commit(self):
        raise RuntimeError("Simulated database commit failure")

    monkeypatch.setattr(session_class, "commit", fail_commit)

    response = user_client.post(f"/checkout/{booking_id}")

    assert response.status_code == 500

    with app.app_context():
        db.session.expire_all()
        booking = db.session.get(Booking, booking_id)
        assert booking.status == original_status
        assert booking.slot.status == original_slot_status

def test_force_checkout_completed_booking_returns_409(admin_client, user_client, make_slot):
    """TC-Admin-03: force checkout of a completed booking returns 409."""
    book(user_client, make_slot())
    assert admin_client.post("/admin/checkout/1").status_code == 302
    response = admin_client.post("/admin/checkout/1")
    assert response.status_code == 409
    assert b"already completed" in response.data


def test_force_checkout_unknown_booking_returns_404(admin_client):
    """TC-Admin-03"""
    assert admin_client.post("/admin/checkout/999").status_code == 404


def test_force_checkout_is_logged_with_admin_id(admin_client, user_client, make_slot, caplog):
    """TC-Admin-03 / SAD 4.4: forced checkouts are logged with the admin id."""
    caplog.set_level(logging.INFO, logger="app.routes.admin")
    book(user_client, make_slot())
    admin_client.post("/admin/checkout/1")
    records = [r for r in caplog.records if getattr(r, "action", None) == "force_checkout"]
    assert len(records) == 1
    assert records[0].user_id is not None


def test_admin_bookings_page_has_confirmation_prompt(admin_client, user_client, make_slot):
    """SAD 4.5: confirm before forced check-out."""
    book(user_client, make_slot())
    page = admin_client.get("/admin/bookings")
    assert b"onsubmit" in page.data
    assert b"/admin/checkout/1" in page.data
