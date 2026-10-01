"""Create demo data: an admin, a customer and 3 floors of slots.
Run once:  python seed.py
Admin login:    admin@vps.com / admin123
Customer login: user@vps.com  / user123
"""
from app import create_app, db
from app.models import ParkingSlot, User

app = create_app()
with app.app_context():
    if not User.query.filter_by(email="admin@vps.com").first():
        admin = User(name="Admin", email="admin@vps.com", role="admin")
        admin.set_password("admin123")
        cust = User(name="Demo User", email="user@vps.com")
        cust.set_password("user123")
        db.session.add_all([admin, cust])
    if ParkingSlot.query.count() == 0:
        for floor in (1, 2, 3):
            for n in range(1, 11):
                db.session.add(ParkingSlot(slot_number=f"F{floor}-{n:02d}", floor=floor))
    db.session.commit()
    print("Seeded.")
