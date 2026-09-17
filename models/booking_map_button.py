from extensions import db
from utils.datetime_utils import naive_utc_now


class BookingMapButton(db.Model):
    """Which Voucher Maps (map buttons) are shown for a specific booking's voucher."""
    __tablename__ = 'booking_map_buttons'
    __table_args__ = (
        db.UniqueConstraint('booking_id', 'map_button_id', name='uq_booking_map_button'),
    )

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer,
                           db.ForeignKey('bookings.id', ondelete='CASCADE'),
                           nullable=False, index=True)
    map_button_id = db.Column(db.Integer,
                              db.ForeignKey('voucher_map_buttons.id', ondelete='CASCADE'),
                              nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=naive_utc_now)

    def __repr__(self):
        return f'<BookingMapButton booking={self.booking_id} map={self.map_button_id}>'
