
import logging

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

    # Avoid adding duplicate handlers if the app is created more than once.
    if not any(getattr(handler, "_vps_log_handler", False)
               for handler in root_logger.handlers):
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

    app.config["SECRET_KEY"] = "change-me-in-production"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///vps.db"

    if config:
        app.config.update(config)

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
