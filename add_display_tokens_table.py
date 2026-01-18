from app import app, db
from models.display_token import DisplayToken
from datetime import datetime, timedelta

def add_display_tokens_table():
    with app.app_context():
        # Create table
        db.create_all()
        
        # Check if sample token exists
        existing = DisplayToken.query.filter_by(name='Main Display').first()
        if not existing:
            # Create sample token
            sample_token = DisplayToken(
                token=DisplayToken.generate_token(),
                name='Main Display',
                description='หน้าจอแสดงคิวหลัก - สำหรับทีวีในร้าน',
                is_active=True,
                created_by='System',
                expires_at=None  # No expiration
            )
            db.session.add(sample_token)
            db.session.commit()
            
            print("✅ Display Tokens table created successfully!")
            print(f"✅ Sample token created:")
            print(f"   Name: {sample_token.name}")
            print(f"   Token: {sample_token.token}")
            print(f"   URL: /queue/display/{sample_token.token}")
        else:
            print("✅ Display Tokens table already exists!")
            print(f"   Existing token: {existing.name} - {existing.token}")

if __name__ == '__main__':
    add_display_tokens_table()
