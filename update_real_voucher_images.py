#!/usr/bin/env python3
"""
Update booking 55 with actual voucher images
"""
import json
from app import app
from models.booking import Booking
from extensions import db
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_voucher_images_to_real():
    with app.app_context():
        try:
            # Query for booking 55
            booking = Booking.query.filter_by(id=55).first()
            
            if not booking:
                logger.error("❌ Booking 55 not found")
                return
            
            logger.info(f"✅ Found booking: {booking.booking_reference}")
            
            # Check what images exist for booking 55
            uploads_dir = os.path.join(os.getcwd(), 'static', 'uploads', 'voucher_images')
            booking_55_images = [f for f in os.listdir(uploads_dir) if f.startswith('booking_55_') and f.endswith('.png')]
            
            logger.info(f"📸 Found {len(booking_55_images)} actual images for booking 55:")
            for img in booking_55_images:
                logger.info(f"  - {img}")
            
            # Create voucher images data structure
            voucher_images = []
            for i, filename in enumerate(booking_55_images, 1):
                voucher_images.append({
                    "id": i,
                    "filename": filename,
                    "path": f"voucher_images/{filename}",
                    "description": f"Voucher Image {i}"
                })
            
            # Set voucher images
            booking.voucher_images = json.dumps(voucher_images, ensure_ascii=False)
            
            # Save changes
            db.session.commit()
            
            logger.info("✅ Successfully updated booking 55 with real voucher images")
            
            # Verify the data
            images = booking.get_voucher_images()
            print(f"📊 Voucher images updated: {len(images)} images")
            for i, image in enumerate(images, 1):
                print(f"  {i}. {image.get('filename')} - {image.get('description')}")
                
        except Exception as e:
            logger.error(f"❌ Error updating voucher images: {e}")
            db.session.rollback()

if __name__ == "__main__":
    update_voucher_images_to_real()