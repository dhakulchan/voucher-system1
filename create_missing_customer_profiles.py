#!/usr/bin/env python3
"""
Script to create missing customer profiles for existing Customer role users
Run this once to migrate existing users who don't have customer profiles yet
"""
from app import app
from extensions import db
from models.user import User
from models.customer import Customer
from utils.logging_config import get_logger

logger = get_logger(__name__)

def create_missing_customer_profiles():
    """Create customer profiles for all Customer role users who don't have one"""
    with app.app_context():
        # Find all Customer role users without customer profile
        users_without_profile = User.query.filter(
            User.role == 'Customer',
            User.customer_profile == None
        ).all()
        
        if not users_without_profile:
            print("✅ All Customer role users already have customer profiles!")
            return
        
        print(f"Found {len(users_without_profile)} Customer users without profiles:")
        print("-" * 80)
        
        created_count = 0
        failed_count = 0
        
        for user in users_without_profile:
            print(f"\n👤 User: {user.username} (ID: {user.id})")
            print(f"   Email: {user.email}")
            
            try:
                # Create customer profile
                customer = Customer(
                    name=user.username,
                    email=user.email,
                    phone='',  # Can be updated later by user
                    customer_type='Visitor-Individual',
                    user_id=user.id,
                    created_by=user.id
                )
                db.session.add(customer)
                db.session.commit()
                
                print(f"   ✅ Customer profile created successfully (Customer ID: {customer.id})")
                created_count += 1
                
            except Exception as e:
                db.session.rollback()
                print(f"   ❌ Failed to create customer profile: {e}")
                logger.error(f"Failed to create customer profile for user {user.id}: {e}")
                failed_count += 1
        
        print("\n" + "=" * 80)
        print(f"📊 Summary:")
        print(f"   ✅ Successfully created: {created_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   📝 Total processed: {len(users_without_profile)}")
        print("=" * 80)

if __name__ == '__main__':
    print("=" * 80)
    print("🔧 Creating Missing Customer Profiles")
    print("=" * 80)
    create_missing_customer_profiles()
