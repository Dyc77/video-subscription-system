from app.db.database import get_db
from sqlalchemy import text

db = next(get_db())

# 1. Check vw_PendingNotifications
print("=== Checking vw_PendingNotifications ===")
query = text("SELECT COUNT(*) as count FROM vw_PendingNotifications")
result = db.execute(query).fetchone()
print(f"Total pending notifications: {result.count}")

if result.count > 0:
    query = text("""
        SELECT user_no, email, video_title, channel_title
        FROM vw_PendingNotifications
        LIMIT 5
    """)
    rows = db.execute(query).fetchall()
    print("\nFirst 5 pending notifications:")
    for row in rows:
        print(f"  - User {row.user_no} ({row.email})")
        print(f"    Video: {row.video_title}")
        print(f"    Channel: {row.channel_title}")

# 2. Check tb_notificationlog
print("\n=== Checking tb_notificationlog ===")
query = text("SELECT COUNT(*) as count FROM tb_notificationlog")
result = db.execute(query).fetchone()
print(f"Total notification logs: {result.count}")

# 3. Check tb_config for param_no=5
print("\n=== Checking notification interval settings ===")
query = text("SELECT user_no, config_value FROM tb_config WHERE param_no = 5")
rows = db.execute(query).fetchall()
if rows:
    for row in rows:
        print(f"  User {row.user_no}: interval = {row.config_value} minutes")
else:
    print("  No interval settings found")

# 4. Check tb_config for param_no=2 (Email)
print("\n=== Checking email notification settings ===")
query = text("SELECT user_no, config_value FROM tb_config WHERE param_no = 2")
rows = db.execute(query).fetchall()
if rows:
    for row in rows:
        status = "ON" if row.config_value == '1' else "OFF"
        print(f"  User {row.user_no}: Email = {status}")
else:
    print("  No email settings found")

db.close()
