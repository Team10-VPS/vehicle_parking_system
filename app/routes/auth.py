import logging

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import User
from app.utils import MIN_PASSWORD_LEN, valid_email

auth_bp = Blueprint("auth", __name__)

logger = logging.getLogger(__name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name:
            flash("Name is required.")
        elif len(name) > 100:
            flash("Name must be 100 characters or fewer.")
        elif not valid_email(email):
            flash("Enter a valid email address.")
        elif len(email) > 120:
            flash("Email must be 120 characters or fewer.")
        elif not password.strip():
            flash("Password is required.")
        elif len(password) < MIN_PASSWORD_LEN:
            flash(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
        elif User.query.filter_by(email=email).first():
            flash("Email already registered.")
        else:
            user = User(name=name, email=email)
            user.set_password(password)
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Email already registered.")
            else:
                flash("Registration successful. Please log in.")
                return redirect(url_for("auth.login"))
    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session.clear()
            session["user_id"] = user.id
            logger.info(
                "user_id=%s action=login_success",
                user.id,
                extra={"user_id": user.id, "action": "login_success"},
            )
            return redirect(url_for("slots.dashboard"))

        logger.warning(
            "user_id=unknown action=login_failure email=%s",
            email,
            extra={"user_id": None, "action": "login_failure"},
        )
        flash("Invalid email or password.")

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    user_id = session.get("user_id")
    if user_id is not None:
        logger.info(
            "user_id=%s action=logout",
            user_id,
            extra={"user_id": user_id, "action": "logout"},
        )
    session.clear()
    return redirect(url_for("auth.login"))
