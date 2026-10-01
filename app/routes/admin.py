from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app import db
from app.models import Booking, ParkingSlot
from app.utils import admin_required, complete_booking

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/slots", methods=["GET", "POST"])
@admin_required
def slots():
    if request.method == "POST":
        number = request.form.get("slot_number", "").strip().upper()
        floor = request.form.get("floor", "").strip()
        if not number or len(number) > 10:
            flash("Slot number is required (max 10 characters).")
        elif not floor.isdigit():
            flash("Floor must be a non-negative number.")
        elif ParkingSlot.query.filter_by(slot_number=number).first():
            flash("Slot number already exists.")
        else:
            db.session.add(ParkingSlot(slot_number=number, floor=int(floor)))
            db.session.commit()
            flash(f"Slot {number} added.")
    all_slots = ParkingSlot.query.order_by(ParkingSlot.floor, ParkingSlot.slot_number).all()
    return render_template("admin_slots.html", slots=all_slots)


@admin_bp.route("/slots/<int:slot_id>/delete", methods=["POST"])
@admin_required
def delete_slot(slot_id):
    slot = db.session.get(ParkingSlot, slot_id)
    if slot is None:
        abort(404)
    if slot.status != "available":
        flash("Cannot remove an occupied slot.")
    else:
        db.session.delete(slot)
        db.session.commit()
        flash("Slot removed.")
    return redirect(url_for("admin.slots"))


@admin_bp.route("/bookings")
@admin_required
def bookings():
    active = Booking.query.filter_by(status="active").order_by(Booking.check_in).all()
    return render_template("admin_bookings.html", bookings=active)


@admin_bp.route("/bookings/<int:booking_id>/force-checkout", methods=["POST"])
@admin_required
def force_checkout(booking_id):
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        abort(404)
    if booking.status == "active":
        complete_booking(booking)
        db.session.commit()
        flash("Booking force checked out.")
    return redirect(url_for("admin.bookings"))
