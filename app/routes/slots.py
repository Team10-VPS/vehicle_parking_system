from collections import OrderedDict

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app import db
from app.models import Booking, ParkingSlot, Vehicle, utcnow
from app.utils import current_user, login_required, valid_plate

slots_bp = Blueprint("slots", __name__)


@slots_bp.route("/")
@login_required
def dashboard():
    slots = ParkingSlot.query.order_by(ParkingSlot.floor, ParkingSlot.slot_number).all()
    floors = OrderedDict()
    for s in slots:
        floors.setdefault(s.floor, []).append(s)
    return render_template("dashboard.html", floors=floors, user=current_user())


@slots_bp.route("/book/<int:slot_id>", methods=["GET", "POST"])
@login_required
def book(slot_id):
    slot = db.session.get(ParkingSlot, slot_id)
    if slot is None:
        flash("Slot not found.")
        return redirect(url_for("slots.dashboard"))
    if slot.status != "available":
        flash("That slot is already occupied.")
        return redirect(url_for("slots.dashboard"))

    if request.method == "POST":
        user = current_user()
        plate = request.form.get("plate", "").strip().upper()
        vtype = request.form.get("vehicle_type", "car").strip().lower()

        if not valid_plate(plate):
            flash("Enter a valid vehicle number (3-15 letters, digits, space or hyphen).")
            return render_template("book.html", slot=slot)
        if vtype not in ("car", "bike", "suv", "van"):
            flash("Invalid vehicle type.")
            return render_template("book.html", slot=slot)

        vehicle = Vehicle.query.filter_by(plate=plate).first()
        if vehicle and vehicle.owner_id != user.id:
            flash("That vehicle is registered to another user.")
            return render_template("book.html", slot=slot)
        if vehicle is None:
            vehicle = Vehicle(plate=plate, vehicle_type=vtype, owner_id=user.id)
            db.session.add(vehicle)
            db.session.flush()

        booking = Booking(user_id=user.id, slot_id=slot.id,
                          vehicle_id=vehicle.id, check_in=utcnow())
        slot.status = "occupied"
        db.session.add(booking)
        db.session.commit()
        flash(f"Slot {slot.slot_number} booked. Checked in.")
        return redirect(url_for("bookings.history"))
    return render_template("book.html", slot=slot)
