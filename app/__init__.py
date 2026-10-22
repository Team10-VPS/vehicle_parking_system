
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config=None):
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vps.db"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = (
        os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    )

    if config:
        app.config.update(config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY must be set in the environment or app config."
        )

    db.init_app(app)

    from app import models  # noqa: F401
    from app.routes.auth import auth_bp
    from app.routes.slots import slots_bp
    from app.routes.bookings import bookings_bp
    from app.routes.admin import admin_bp

    for bp in (auth_bp, slots_bp, bookings_bp, admin_bp):
        app.register_blueprint(bp)

    from app.utils import current_user

    @app.context_processor
    def inject_user():
        return {"current_user": current_user()}

    with app.app_context():
        db.create_all()

    return app
