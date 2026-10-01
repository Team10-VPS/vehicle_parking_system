from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config=None):
    app = Flask(__name__)
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
