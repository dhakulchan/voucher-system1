#!/usr/bin/env python3
"""Link User accounts to Customer records by email"""

from app import app, db
from models import User
from models.customer import Customer

with app.app_context():
    users = User.query.filter_by(role='Customer').all()
    
    print(f"📊 Found {len(users)} Customer users")
    
    linked_count = 0
    for user in users:
        customer = Customer.query.filter_by(email=user.email).first()
        
        if customer:
            print(f"✅ User {user.username} ({user.email}) -> Customer ID {customer.id}")
            # ถ้า User มี customer_id field
            if hasattr(user, 'customer_id'):
                user.customer_id = customer.id
                linked_count += 1
            else:
                print(f"⚠️  User model doesn't have customer_id field")
        else:
            print(f"❌ No customer found for {user.email}")
    
    if linked_count > 0:
        db.session.commit()
        print(f"\n✅ Linked {linked_count} users to customers")
    else:
        print("\n⚠️  User model needs customer_id field added")
