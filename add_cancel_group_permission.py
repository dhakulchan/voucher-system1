import mysql.connector

# Database connection
conn = mysql.connector.connect(
    host="localhost",
    user="voucher_user",
    password="VoucherSecure2026!",
    database="voucher_enhanced"
)

cursor = conn.cursor()

# Get current permissions for admin user (ID=3)
cursor.execute("SELECT id, permissions FROM user_permissions WHERE user_id = 3")
result = cursor.fetchone()

if result:
    user_perm_id, permissions_json = result
    
    import json
    permissions = json.loads(permissions_json)
    
    # Add cancel_group permission to group_buy section
    if 'group_buy' not in permissions:
        permissions['group_buy'] = {}
    
    permissions['group_buy']['cancel_group'] = True
    
    # Update database
    updated_json = json.dumps(permissions, ensure_ascii=False)
    cursor.execute(
        "UPDATE user_permissions SET permissions = %s WHERE id = %s",
        (updated_json, user_perm_id)
    )
    
    conn.commit()
    print(f"✅ Added cancel_group permission to admin user (ID=3)")
    print(f"   Group Buy permissions: {permissions.get('group_buy', {})}")
else:
    print("❌ User permissions not found for user ID 3")

cursor.close()
conn.close()
