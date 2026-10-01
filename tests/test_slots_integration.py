"""Slot display and booking integration tests."""
import time

from app import db
from app.models import Booking, ParkingSlot, Vehicle


def test_dashboard_lists_slots(user_client, make_slot):
    """TC-Slot-01"""
    make_slot("A-01", 1)
    make_slot("A-02", 1, "occupied")
    r = user_client.get("/")
    assert b"A-01" in r.data and b"A-02" in r.data


def test_dashboard_groups_by_floor(user_client, make_slot):
    """TC-Slot-02"""
    make_slot("B-01", 2)
    make_slot("A-01", 1)
    body = user_client.get("/").data.decode()
    assert body.index("Floor 1") < body.index("A-01") < body.index("Floor 2") < body.index("B-01")


def test_dashboard_empty(user_client):
    """TC-Slot-01 boundary: no slots"""
    assert b"No parking slots available" in user_client.get("/").data


def test_book_available_slot(user_client, make_slot, app):
    """TC-Book-01 / TC-Book-02 / TC-Book-04 / TC-Rel-01"""
    sid = make_slot()
    r = user_client.post(f"/book/{sid}", data={"plate": "ka01ab1234", "vehicle_type": "car"},
                         follow_redirects=True)
    assert b"booked" in r.data
    with app.app_context():
        assert db.session.get(ParkingSlot, sid).status == "occupied"
        b = Booking.query.one()
        assert b.status == "active" and b.check_in is not None and b.check_out is None
        assert Vehicle.query.one().plate == "KA01AB1234"


def test_cannot_book_occupied_slot(user_client, make_slot, app):
    """TC-Slot-03"""
    sid = make_slot(status="occupied")
    r = user_client.post(f"/book/{sid}", data={"plate": "KA01AB1234"}, follow_redirects=True)
    assert b"already occupied" in r.data
    with app.app_context():
        assert Booking.query.count() == 0


def test_book_nonexistent_slot(user_client):
    r = user_client.post("/book/999", data={"plate": "KA01AB1234"}, follow_redirects=True)
    assert b"Slot not found" in r.data


def test_booking_reuses_existing_vehicle(user_client, make_slot, app):
    """TC-Book-03"""
    s1, s2 = make_slot("A-01"), make_slot("A-02")
    user_client.post(f"/book/{s1}", data={"plate": "KA01AB1234"})
    with app.app_context():
        first = Booking.query.one()
        first.status = "completed"
        first.slot.status = "available"
        db.session.commit()
    user_client.post(f"/book/{s2}", data={"plate": "KA01AB1234"})
    with app.app_context():
        assert Vehicle.query.count() == 1
        assert Booking.query.count() == 2


def test_booking_invalid_plate_rejected(user_client, make_slot, app):
    """TC-Book-02 error / TC-Sec-04"""
    sid = make_slot()
    r = user_client.post(f"/book/{sid}", data={"plate": "<b>"})
    assert b"valid vehicle number" in r.data
    with app.app_context():
        assert Booking.query.count() == 0
        assert db.session.get(ParkingSlot, sid).status == "available"


def test_booking_requires_login(client, make_slot):
    sid = make_slot()
    assert client.post(f"/book/{sid}", data={"plate": "KA01AB1234"}).status_code == 302


def test_dashboard_performance_200_slots(user_client, make_slot, app):
    """TC-Perf-01: <= 2 seconds for 200 slots"""
    with app.app_context():
        db.session.add_all([ParkingSlot(slot_number=f"S{i}", floor=i % 5) for i in range(200)])
        db.session.commit()
    start = time.perf_counter()
    r = user_client.get("/")
    assert r.status_code == 200
    assert time.perf_counter() - start <= 2.0
