"""
Delete queue 260101 if it exists (stuck/duplicate queue)
"""
from app import app, db
from models.queue import Queue

def cleanup_queue_260101():
    """Remove queue 260101 if it exists"""
    with app.app_context():
        queue = Queue.query.filter_by(queue_number='260101').first()
        
        if queue:
            print(f"🗑️ Found stuck queue 260101:")
            print(f"  ID: {queue.id}")
            print(f"  Customer: {queue.customer_name}")
            print(f"  Phone: {queue.customer_phone}")
            print(f"  Status: {queue.status}")
            print(f"  Created: {queue.created_at}")
            
            confirm = input("\n⚠️ Delete this queue? (yes/no): ")
            if confirm.lower() == 'yes':
                db.session.delete(queue)
                db.session.commit()
                print("✅ Queue 260101 deleted successfully")
            else:
                print("❌ Deletion cancelled")
        else:
            print("✅ Queue 260101 not found (database is clean)")
        
        # Show current queues
        from datetime import date
        today = date.today()
        prefix = today.strftime('%y%m')
        
        queues = Queue.query.filter(
            Queue.queue_number.like(f'{prefix}%')
        ).order_by(Queue.queue_number.asc()).all()
        
        print(f"\n📊 Current queues for today ({prefix}): {len(queues)} total")
        for q in queues[:10]:  # Show first 10
            print(f"  {q.queue_number}: {q.customer_name} (Status: {q.status})")
        
        if len(queues) > 10:
            print(f"  ... and {len(queues) - 10} more")

if __name__ == '__main__':
    cleanup_queue_260101()
