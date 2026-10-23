import logging
import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class SafeFormatter(logging.Formatter):
    """Format logs safely when user ID or action fields are missing."""

    def format(self, record):
        if not hasattr(record, "user_id"):
            record.user_id = "unknown"
        if not hasattr(record, "action"):
            record.action = "general"
        return super().format(record)


def configure_logging():
    """Configure consistent logging for the application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if not any(
        getattr(handler, "_vps_log_handler", False)
        for handler in root_logger.handlers
    ):
        handler = logging.StreamHandler()
        handler._vps_log_handler = True
        handler.setFormatter(
            SafeFormatter(
                "%(asctime)s %(levelname)s "
                "user_id=%(user_id)s action=%(action)s %(message)s"
            )
        )
        root_logger.addHandler(handler)


def create_app(config=None):
    app = Flask(__name__)
    configure_logging()

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
    from app.utils import current_user
    from app.routes.auth import auth_bp
    from app.routes.slots import slots_bp
    from app.routes.vehicles import vehicles_bp
    from app.routes.bookings import bookings_bp
    from app.routes.admin import admin_bp

    for bp in (auth_bp, slots_bp, bookings_bp, admin_bp, vehicles_bp):
        app.register_blueprint(bp)

    @app.context_processor
    def inject_current_user():
        return {"current_user": current_user()}

    with app.app_context():
        db.create_all()

    return app
