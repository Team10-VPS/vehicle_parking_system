"""Slot display and booking integration tests."""
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from app import create_app, db
from app.models import Booking, ParkingSlot, User, Vehicle
from tests.conftest import login


def test_dashboard_lists_slots(user_client, make_slot):
    """TC-Slot-01"""
    make_slot("A-01", 1)
    make_slot("A-02", 1, "occupied")
    r = user_client.get("/")
    assert b"A-01" in r.data and b"A-02" in r.data


def test_dashboard_route(user_client):
    """Dashboard is accessible at /dashboard."""
    response = user_client.get("/dashboard")

    assert response.status_code == 200
    assert b"Parking Slots" in response.data



def test_dashboard_groups_by_floor(user_client, make_slot):
    """TC-Slot-02"""
    make_slot("B-01", 2)
    make_slot("A-01", 1)
    body = user_client.get("/").data.decode()
    assert body.index("Floor 1") < body.index("A-01") < body.index("Floor 2") < body.index("B-01")

def test_dashboard_orders_slots_by_floor_and_number(
    user_client, make_slot
):
    """Slots are ordered by floor, then slot number."""
    make_slot("A-02", 1)
    make_slot("A-01", 1)
    make_slot("B-01", 2)

    response = user_client.get("/dashboard")
    body = response.data.decode()

    assert body.index("Floor 1") < body.index("Floor 2")
    assert body.index("A-01") < body.index("A-02")
    assert body.index("A-02") < body.index("B-01")


def test_dashboard_empty(user_client):
    """TC-Slot-01 boundary: no slots"""
    assert b"No parking slots available" in user_client.get("/").data


def test_booking_form_posts_required_fields(user_client, make_slot):
    """TC-Book-01: the form submits the selected slot to POST /book."""
    sid = make_slot()
    response = user_client.get(f"/book/{sid}")
    assert response.status_code == 200
    assert b'action="/book"' in response.data
    assert f'name="slot_id" value="{sid}"'.encode() in response.data
    assert b'name="vehicle_number"' in response.data
    assert b'name="vehicle_type"' in response.data


def test_book_available_slot(user_client, make_slot, app):
    """TC-Book-01 / TC-Book-02 / TC-Book-04 / TC-Rel-01"""
    sid = make_slot()
    r = user_client.post("/book", data={"slot_id": sid, "vehicle_number": "ka01ab1234", "vehicle_type": "car"},
                         follow_redirects=True)
    assert b"booked" in r.data
    with app.app_context():
        assert db.session.get(ParkingSlot, sid).status == "occupied"
        b = Booking.query.one()
        assert b.status == "active" and b.check_in is not None and b.check_out is None
        assert Vehicle.query.one().plate == "KA01AB1234"

    dashboard = user_client.get("/").data
    assert f'href="/book/{sid}"'.encode() not in dashboard
    assert b'class="slot occupied"' in dashboard


def test_only_customers_can_select_or_book_slots(admin_client, make_slot, app):
    """TC-Slot-03: admins cannot use the customer booking workflow."""
    sid = make_slot()
    dashboard = admin_client.get("/").data
    assert f'href="/book/{sid}"'.encode() not in dashboard
    assert b'class="slot available"' in dashboard
    assert admin_client.get(f"/book/{sid}").status_code == 403
    response = admin_client.post("/book", data={
        "slot_id": sid, "vehicle_number": "KA01AB1234", "vehicle_type": "car"
    })
    assert response.status_code == 403
    with app.app_context():
        assert db.session.get(ParkingSlot, sid).status == "available"
        assert Booking.query.count() == Vehicle.query.count() == 0


def test_two_customers_cannot_book_same_slot(user_client, make_slot, make_user, app):
    """TC-Slot-03 / TC-Book-01 / TC-Rel-01: only one booking succeeds."""
    sid = make_slot()
    make_user(email="second@test.com")
    second_client = app.test_client()
    login(second_client, "second@test.com")

    first = user_client.post("/book", data={
        "slot_id": sid, "vehicle_number": "KA01AB1234", "vehicle_type": "car"
    })
    second = second_client.post("/book", data={
        "slot_id": sid, "vehicle_number": "KA02CD5678", "vehicle_type": "car"
    })

    assert first.status_code == 302
    assert second.status_code == 409
    with app.app_context():
        assert Booking.query.filter_by(slot_id=sid, status="active").count() == 1
        assert Vehicle.query.count() == 1
        assert db.session.get(ParkingSlot, sid).status == "occupied"


def test_available_status_cannot_override_active_booking(user_client, make_slot, app):
    """TC-Rel-01: a stale slot status cannot create another active booking."""
    sid = make_slot()
    user_client.post("/book", data={
        "slot_id": sid, "vehicle_number": "KA01AB1234", "vehicle_type": "car"
    })
    with app.app_context():
        db.session.get(ParkingSlot, sid).status = "available"
        db.session.commit()

    response = user_client.post("/book", data={
        "slot_id": sid, "vehicle_number": "KA02CD5678", "vehicle_type": "car"
    })
    assert response.status_code == 409
    with app.app_context():
        assert Booking.query.filter_by(slot_id=sid, status="active").count() == 1
        assert Vehicle.query.count() == 1


def test_simultaneous_requests_create_at_most_one_booking(tmp_path):
    """TC-Rel-01: concurrent customers cannot both claim the same slot."""
    database_uri = f"sqlite:///{(tmp_path / 'bookings.db').as_posix()}"
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": database_uri})
    with app.app_context():
        for email in ("first@test.com", "second@test.com"):
            user = User(name=email, email=email)
            user.set_password("secret123")
            db.session.add(user)
        slot = ParkingSlot(slot_number="A-01", floor=1)
        db.session.add(slot)
        db.session.commit()
        slot_id = slot.id

    barrier = Barrier(2)

    def attempt(email, plate):
        client = app.test_client()
        login(client, email)
        barrier.wait(timeout=10)
        return client.post("/book", data={
            "slot_id": slot_id, "vehicle_number": plate, "vehicle_type": "car"
        }).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(attempt, "first@test.com", "KA01AB1234")
        second = pool.submit(attempt, "second@test.com", "KA02CD5678")
        statuses = sorted((first.result(), second.result()))

    assert statuses == [302, 409]
    with app.app_context():
        assert Booking.query.filter_by(slot_id=slot_id, status="active").count() == 1
        assert Vehicle.query.count() == 1
        assert db.session.get(ParkingSlot, slot_id).status == "occupied"


def test_cannot_book_occupied_slot(user_client, make_slot, app):
    """TC-Slot-03"""
    sid = make_slot(status="occupied")
    r = user_client.post("/book", data={"slot_id": sid, "vehicle_number": "KA01AB1234", "vehicle_type": "car"})
    assert r.status_code == 409
    assert b"already occupied" in r.data
    with app.app_context():
        assert Booking.query.count() == 0


def test_book_nonexistent_slot(user_client):
    r = user_client.post("/book", data={"slot_id": 999, "vehicle_number": "KA01AB1234", "vehicle_type": "car"})
    assert r.status_code == 404
    assert b"Slot not found" in r.data


def test_booking_reuses_existing_vehicle(user_client, make_slot, app):
    """TC-Book-03"""
    s1, s2 = make_slot("A-01"), make_slot("A-02")
    user_client.post("/book", data={"slot_id": s1, "vehicle_number": "KA01AB1234", "vehicle_type": "car"})
    with app.app_context():
        first = Booking.query.one()
        first.status = "completed"
        first.slot.status = "available"
        db.session.commit()
    user_client.post("/book", data={"slot_id": s2, "vehicle_number": "KA01AB1234", "vehicle_type": "car"})
    with app.app_context():
        assert Vehicle.query.count() == 1
        assert Booking.query.count() == 2


def test_booking_invalid_plate_rejected(user_client, make_slot, app):
    """TC-Book-02 error / TC-Sec-04"""
    sid = make_slot()
    r = user_client.post("/book", data={"slot_id": sid, "vehicle_number": "<b>", "vehicle_type": "car"})
    assert r.status_code == 400
    assert b"valid vehicle number" in r.data
    with app.app_context():
        assert Booking.query.count() == 0
        assert db.session.get(ParkingSlot, sid).status == "available"


def test_booking_requires_login(client, make_slot):
    sid = make_slot()
    assert client.post("/book", data={"slot_id": sid, "vehicle_number": "KA01AB1234", "vehicle_type": "car"}).status_code == 302


@pytest.mark.parametrize("field,value", [
    ("slot_id", ""), ("slot_id", "abc"), ("slot_id", "-1"),
    ("slot_id", "9" * 100),
    ("vehicle_number", ""), ("vehicle_type", "truck"),
])
def test_booking_rejects_invalid_input(user_client, make_slot, app, field, value):
    """TC-Book-02 / TC-Book-04: malformed form data returns 400 with no changes."""
    sid = make_slot()
    data = {"slot_id": str(sid), "vehicle_number": "KA01AB1234", "vehicle_type": "car"}
    data[field] = value
    response = user_client.post("/book", data=data)
    assert response.status_code == 400
    assert b"flash" in response.data
    with app.app_context():
        assert db.session.get(ParkingSlot, sid).status == "available"
        assert Booking.query.count() == Vehicle.query.count() == 0


def test_booking_rolls_back_database_failure(user_client, make_slot, app):
    """TC-Book-04: a failed insert leaves the slot and vehicle unchanged."""
    sid = make_slot()

    def fail_booking_insert(_mapper, _connection, _target):
        raise SQLAlchemyError("simulated insert failure")

    event.listen(Booking, "before_insert", fail_booking_insert)
    try:
        response = user_client.post("/book", data={
            "slot_id": sid, "vehicle_number": "KA01AB1234", "vehicle_type": "car"
        })
    finally:
        event.remove(Booking, "before_insert", fail_booking_insert)
    assert response.status_code == 500
    assert b"Booking could not be completed" in response.data
    with app.app_context():
        assert db.session.get(ParkingSlot, sid).status == "available"
        assert Booking.query.count() == Vehicle.query.count() == 0


def test_dashboard_performance_200_slots(user_client, make_slot, app):
    """TC-Perf-01: <= 2 seconds for 200 slots"""
    with app.app_context():
        db.session.add_all([ParkingSlot(slot_number=f"S{i}", floor=i % 5) for i in range(200)])
        db.session.commit()
    start = time.perf_counter()
    r = user_client.get("/")
    assert r.status_code == 200
    assert time.perf_counter() - start <= 2.0
