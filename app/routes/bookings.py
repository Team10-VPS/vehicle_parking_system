from flask import Blueprint, abort, flash, redirect, render_template, url_for

from app import db
from app.models import Booking
from app.utils import complete_booking, current_user, login_required

bookings_bp = Blueprint("bookings", __name__)


@bookings_bp.route("/history")
@login_required
def history():
    user = current_user()
    bookings = (Booking.query.filter_by(user_id=user.id)
                .order_by(Booking.check_in.desc()).all())
    return render_template("history.html", bookings=bookings)


@bookings_bp.route("/checkout/<int:booking_id>", methods=["POST"])
@login_required
def checkout(booking_id):
    user = current_user()
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        abort(404)
    if booking.user_id != user.id and not user.is_admin:
        abort(403)
    if booking.status != "active":
        flash("Booking already checked out.")
        return redirect(url_for("bookings.history"))
    complete_booking(booking)
    db.session.commit()
    flash("Checked out successfully.")
    return redirect(url_for("bookings.history"))
