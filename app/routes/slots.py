from collections import OrderedDict

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.models import Booking, ParkingSlot, Vehicle, utcnow
from app.utils import current_user, login_required, valid_plate

slots_bp = Blueprint("slots", __name__)


@slots_bp.route("/", endpoint="home")
@slots_bp.route("/dashboard")
@login_required
def dashboard():
    slots = ParkingSlot.query.order_by(ParkingSlot.floor, ParkingSlot.slot_number).all()
    floors = OrderedDict()
    for s in slots:
        floors.setdefault(s.floor, []).append(s)
    return render_template("dashboard.html", floors=floors, user=current_user())


@slots_bp.route("/book/<int:slot_id>", methods=["GET"])
@login_required
def book(slot_id):
    if current_user().role != "customer":
        abort(403)
    slot = db.session.get(ParkingSlot, slot_id)
    if slot is None:
        flash("Slot not found.")
        return redirect(url_for("slots.dashboard"))
    if slot.status != "available":
        flash("That slot is already occupied.")
        return redirect(url_for("slots.dashboard"))

    return render_template("book.html", slot=slot)


def booking_error(message, status, slot=None):
    db.session.rollback()
    flash(message)
    if slot is not None:
        return render_template("book.html", slot=slot), status
    return dashboard(), status


@slots_bp.route("/book", methods=["POST"])
@login_required
def create_booking():
    user = current_user()
    if user.role != "customer":
        abort(403)

    raw_slot_id = request.form.get("slot_id", "").strip()
    plate = request.form.get("vehicle_number", "").strip().upper()
    vtype = request.form.get("vehicle_type", "").strip().lower()

    if not raw_slot_id or not raw_slot_id.isascii() or not raw_slot_id.isdecimal():
        return booking_error("Enter a valid slot ID.", 400)
    try:
        slot_id = int(raw_slot_id)
    except ValueError:
        return booking_error("Enter a valid slot ID.", 400)
    if slot_id < 1 or slot_id > 2**63 - 1:
        return booking_error("Enter a valid slot ID.", 400)
    if not valid_plate(plate):
        return booking_error("Enter a valid vehicle number (3-15 letters, digits, space or hyphen).", 400)
    if vtype not in ("car", "bike", "suv", "van"):
        return booking_error("Invalid vehicle type.", 400)

    slot = db.session.get(ParkingSlot, slot_id)
    if slot is None:
        return booking_error("Slot not found.", 404)
    if slot.status != "available":
        return booking_error("That slot is already occupied.", 409)

    vehicle = Vehicle.query.filter_by(plate=plate).first()
    if vehicle and vehicle.owner_id != user.id:
        return booking_error("That vehicle is registered to another user.", 409, slot)

    try:
        # Claim the slot only if it is free and has no active booking.
        active_booking = select(Booking.id).where(
            Booking.slot_id == ParkingSlot.id, Booking.status == "active"
        ).exists()
        claimed = db.session.execute(
            update(ParkingSlot)
            .where(ParkingSlot.id == slot_id, ParkingSlot.status == "available", ~active_booking)
            .values(status="occupied")
        ).rowcount
        if claimed != 1:
            db.session.rollback()
            current_slot = db.session.get(ParkingSlot, slot_id, populate_existing=True)
            if current_slot is None:
                return booking_error("Slot not found.", 404)
            return booking_error("That slot is already occupied.", 409)

        if vehicle is None:
            vehicle = Vehicle(plate=plate, vehicle_type=vtype, owner_id=user.id)
            db.session.add(vehicle)
            db.session.flush()

        db.session.add(Booking(user_id=user.id, slot_id=slot_id,
                               vehicle_id=vehicle.id, check_in=utcnow()))
        db.session.commit()
    except SQLAlchemyError:
        return booking_error("Booking could not be completed.", 500)

    flash(f"Slot {slot.slot_number} booked. Checked in.")
    return redirect(url_for("bookings.history"))
