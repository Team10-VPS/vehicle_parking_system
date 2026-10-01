"""Check-out, history and admin integration tests."""
from app import db
from app.models import Booking, ParkingSlot
from tests.conftest import login


def book(client, sid, plate="KA01AB1234"):
    return client.post(f"/book/{sid}", data={"plate": plate}, follow_redirects=True)


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


def test_double_checkout_blocked(user_client, make_slot):
    """TC-Checkout-01 boundary"""
    book(user_client, make_slot())
    user_client.post("/checkout/1")
    r = user_client.post("/checkout/1", follow_redirects=True)
    assert b"already checked out" in r.data


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
    admin_client.post("/admin/bookings/1/force-checkout")
    with app.app_context():
        assert db.session.get(Booking, 1).status == "completed"
        assert db.session.get(ParkingSlot, sid).status == "available"


def test_non_admin_blocked_from_admin_routes(user_client):
    """TC-Sec-03 / VPS-SR-002"""
    assert user_client.get("/admin/slots").status_code == 403
    assert user_client.get("/admin/bookings").status_code == 403
    assert user_client.post("/admin/slots", data={"slot_number": "X", "floor": "1"}).status_code == 403
    assert user_client.post("/admin/bookings/1/force-checkout").status_code == 403


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
