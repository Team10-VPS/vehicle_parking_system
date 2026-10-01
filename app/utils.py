import re
from functools import wraps

from flask import abort, redirect, session, url_for

from app import db
from app.models import User, utcnow

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PLATE_RE = re.compile(r"^[A-Za-z0-9\- ]{3,15}$")
MIN_PASSWORD_LEN = 6


def valid_email(email):
    return bool(email and EMAIL_RE.match(email))


def valid_plate(plate):
    return bool(plate and PLATE_RE.match(plate))


def current_user():
    uid = session.get("user_id")
    return db.session.get(User, uid) if uid else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user():
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return redirect(url_for("auth.login"))
        if not user.is_admin:
            abort(403)
        return view(*args, **kwargs)
    return wrapped


def complete_booking(booking):
    """Close an active booking and free its slot."""
    booking.check_out = utcnow()
    booking.status = "completed"
    booking.slot.status = "available"
