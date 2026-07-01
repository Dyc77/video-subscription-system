"""
測試通知發送函數是否被調用
"""
from app.db.database import get_db
from app.services.watcher_service import WatcherService
from sqlalchemy import text

print("=" * 60)
print("測試通知發送函數調用")
print("=" * 60)

db = next(get_db())

try:
    # 創建 WatcherService 實例
    watcher = WatcherService(db)

    # 1. 檢查 vw_PendingNotifications
    print("\n【步驟 1】檢查待發送通知...")
    query = text("SELECT COUNT(*) as count FROM vw_PendingNotifications")
    result = db.execute(query).fetchone()
    print(f"待發送通知數量: {result.count}")

    # 2. 直接調用 _send_notifications_from_view
    print("\n【步驟 2】直接調用 _send_notifications_from_view()...")
    watcher._send_notifications_from_view()

    # 3. 檢查 tb_notificationlog
    print("\n【步驟 3】檢查通知記錄...")
    query = text("SELECT COUNT(*) as count FROM tb_notificationlog")
    result = db.execute(query).fetchone()
    print(f"通知記錄數量: {result.count}")

    if result.count > 0:
        query = text("SELECT * FROM tb_notificationlog ORDER BY send_time DESC LIMIT 5")
        logs = db.execute(query).fetchall()
        print("\n最新 5 筆記錄:")
        for log in logs:
            print(f"  log_id={log.log_id}, user_no={log.user_no}, video_no={log.video_no}, send_time={log.send_time}")

except Exception as e:
    print(f"\nERROR: {str(e)}")
    import traceback
    traceback.print_exc()

finally:
    db.close()

print("\n" + "=" * 60)
print("測試完成")
print("=" * 60)
