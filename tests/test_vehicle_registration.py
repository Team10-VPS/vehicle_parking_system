"""Vehicle registration and booking association integration tests."""

import pytest
from sqlalchemy import event
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Booking, ParkingSlot, Vehicle
from tests.conftest import login


def test_register_vehicle_and_book_with_it(user_client, make_slot, app):
    """TC-Book-02 / TC-Book-03: an owned registered vehicle links to its booking."""
    response = user_client.post("/vehicles", data={
        "vehicle_number": "ka01ab1234", "vehicle_type": "bike"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"KA01AB1234" in response.data

    slot_id = make_slot()
    with app.app_context():
        vehicle = Vehicle.query.one()
        vehicle_id = vehicle.id
        owner_id = vehicle.owner_id
    form = user_client.get(f"/book/{slot_id}")
    assert f'value="{vehicle_id}"'.encode() in form.data
    response = user_client.post("/book", data={"slot_id": slot_id, "vehicle_id": vehicle_id})
    assert response.status_code == 302
    with app.app_context():
        booking = Booking.query.one()
        assert (booking.user_id, booking.vehicle_id) == (owner_id, vehicle_id)
        assert Vehicle.query.count() == 1


@pytest.mark.parametrize("plate,vehicle_type", [
    ("", "car"), ("<script>", "car"), ("KA01AB1234", "truck")
])
def test_vehicle_registration_rejects_invalid_details(
    user_client, app, plate, vehicle_type
):
    """TC-Book-04: invalid vehicle details create no record."""
    response = user_client.post("/vehicles", data={
        "vehicle_number": plate, "vehicle_type": vehicle_type
    })
    assert response.status_code == 400
    assert b"flash" in response.data
    with app.app_context():
        assert Vehicle.query.count() == 0


def test_vehicle_number_is_unique_across_customers(user_client, make_user, app):
    """TC-Book-02: a plate already owned by another customer cannot be registered."""
    user_client.post("/vehicles", data={"vehicle_number": "KA01AB1234", "vehicle_type": "car"})
    make_user(email="second@test.com")
    other = app.test_client()
    login(other, "second@test.com")
    assert b"KA01AB1234" not in other.get("/vehicles").data
    response = other.post("/vehicles", data={"vehicle_number": "ka01ab1234", "vehicle_type": "car"})
    assert response.status_code == 409
    with app.app_context():
        assert Vehicle.query.count() == 1


def test_cannot_book_another_customers_vehicle(user_client, make_user, make_slot, app):
    """TC-Book-03 / TC-Book-04: forged vehicle IDs cannot create a booking."""
    user_client.post("/vehicles", data={"vehicle_number": "KA01AB1234", "vehicle_type": "car"})
    with app.app_context():
        vehicle_id = Vehicle.query.one().id
    make_user(email="second@test.com")
    other = app.test_client()
    login(other, "second@test.com")
    slot_id = make_slot()
    response = other.post("/book", data={"slot_id": slot_id, "vehicle_id": vehicle_id})
    assert response.status_code == 403
    assert b"registered vehicles" in response.data
    with app.app_context():
        assert Booking.query.count() == 0
        assert db.session.get(ParkingSlot, slot_id).status == "available"


@pytest.mark.parametrize("vehicle_id", ["abc", "-1", "9" * 5000])
def test_booking_rejects_invalid_vehicle_id(user_client, make_slot, app, vehicle_id):
    """TC-Book-04: malformed vehicle IDs do not create bookings."""
    slot_id = make_slot()
    response = user_client.post("/book", data={"slot_id": slot_id, "vehicle_id": vehicle_id})
    assert response.status_code == 400
    with app.app_context():
        assert Booking.query.count() == 0
        assert db.session.get(ParkingSlot, slot_id).status == "available"


def test_selected_vehicle_booking_rolls_back_on_failure(user_client, make_slot, app):
    """TC-Book-04: failed booking retains the vehicle but does not claim the slot."""
    user_client.post("/vehicles", data={"vehicle_number": "KA01AB1234", "vehicle_type": "car"})
    with app.app_context():
        vehicle_id = Vehicle.query.one().id
    slot_id = make_slot()

    def fail_insert(_mapper, _connection, _target):
        raise SQLAlchemyError("simulated insert failure")

    event.listen(Booking, "before_insert", fail_insert)
    try:
        response = user_client.post("/book", data={"slot_id": slot_id, "vehicle_id": vehicle_id})
    finally:
        event.remove(Booking, "before_insert", fail_insert)
    assert response.status_code == 500
    with app.app_context():
        assert Booking.query.count() == 0
        assert Vehicle.query.count() == 1
        assert db.session.get(ParkingSlot, slot_id).status == "available"


def test_vehicle_registration_requires_login(client, app):
    assert client.get("/vehicles").status_code == 302
    assert client.post("/vehicles", data={
        "vehicle_number": "KA01AB1234", "vehicle_type": "car"
    }).status_code == 302
    with app.app_context():
        assert Vehicle.query.count() == 0
