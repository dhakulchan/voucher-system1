"""Create the booking_map_buttons table (per-booking Voucher Maps selection).

create_all() only creates the table if missing, so this is safe to re-run.

    cd /var/www/booking && venv/bin/python add_booking_map_buttons_table.py
"""
from app import app
from extensions import db
import models.map_button  # noqa: F401
import models.booking_map_button  # noqa: F401
from models.booking_map_button import BookingMapButton


def main():
    with app.app_context():
        db.create_all()
        print(f"✅ booking_map_buttons ready ({BookingMapButton.query.count()} rows)")


if __name__ == '__main__':
    main()
