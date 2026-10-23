from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app import db
from app.models import Vehicle
from app.utils import current_user, login_required, valid_plate, valid_vehicle_type

vehicles_bp = Blueprint("vehicles", __name__)


@vehicles_bp.route("/vehicles", methods=["GET", "POST"])
@login_required
def index():
    user = current_user()
    if request.method == "POST":
        plate = request.form.get("vehicle_number", "").strip().upper()
        vehicle_type = request.form.get("vehicle_type", "").strip().lower()
        if not valid_plate(plate):
            flash("Enter a valid vehicle number (3-15 letters, digits, space or hyphen).")
            return render_template("vehicles.html", vehicles=owned_vehicles(user.id)), 400
        if not valid_vehicle_type(vehicle_type):
            flash("Invalid vehicle type.")
            return render_template("vehicles.html", vehicles=owned_vehicles(user.id)), 400
        if Vehicle.query.filter_by(plate=plate).first():
            flash("That vehicle number is already registered.")
            return render_template("vehicles.html", vehicles=owned_vehicles(user.id)), 409

        db.session.add(Vehicle(plate=plate, vehicle_type=vehicle_type, owner_id=user.id))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("That vehicle number is already registered.")
            return render_template("vehicles.html", vehicles=owned_vehicles(user.id)), 409
        except SQLAlchemyError:
            db.session.rollback()
            flash("Vehicle could not be registered.")
            return render_template("vehicles.html", vehicles=owned_vehicles(user.id)), 500
        flash("Vehicle registered successfully.")
        return redirect(url_for("vehicles.index"))

    return render_template("vehicles.html", vehicles=owned_vehicles(user.id))


def owned_vehicles(user_id):
    return Vehicle.query.filter_by(owner_id=user_id).order_by(Vehicle.plate).all()
