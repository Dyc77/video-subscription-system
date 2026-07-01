"""
測試完整通知系統

這個腳本會：
1. 檢查資料庫連線
2. 檢查 View 是否正確建立
3. 查詢待發送通知清單
4. 測試發送通知功能

使用方法：
    py backend/test_notification_system.py
"""

import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.db.database import SessionLocal
from app.services.watcher_service import WatcherService
from sqlalchemy import text
import logging

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_database_connection():
    """測試資料庫連線"""
    print("=" * 60)
    print("🔍 測試資料庫連線")
    print("=" * 60)

    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1"))
        print("✅ 資料庫連線成功！")
        db.close()
        return True
    except Exception as e:
        print(f"❌ 資料庫連線失敗：{str(e)}")
        return False


def test_view_exists():
    """檢查 vw_PendingNotifications View 是否存在"""
    print()
    print("=" * 60)
    print("🔍 檢查 vw_PendingNotifications View")
    print("=" * 60)

    try:
        db = SessionLocal()

        # 檢查 View 是否存在
        result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM information_schema.VIEWS
            WHERE TABLE_SCHEMA = 'db_youtubesubscribe'
            AND TABLE_NAME = 'vw_pendingnotifications'
        """))

        count = result.fetchone()[0]

        if count > 0:
            print("✅ vw_PendingNotifications View 存在")

            # 嘗試查詢 View
            result = db.execute(text("SELECT COUNT(*) as total FROM vw_PendingNotifications"))
            total = result.fetchone()[0]
            print(f"📊 目前有 {total} 筆待發送通知")

            db.close()
            return True
        else:
            print("❌ vw_PendingNotifications View 不存在")
            print("   請執行 update_for_notification.sql 建立 View")
            db.close()
            return False

    except Exception as e:
        print(f"❌ 檢查失敗：{str(e)}")
        if db:
            db.close()
        return False


def test_system_params():
    """檢查系統參數是否正確設定"""
    print()
    print("=" * 60)
    print("🔍 檢查系統參數")
    print("=" * 60)

    try:
        db = SessionLocal()

        # 查詢通知相關參數
        result = db.execute(text("""
            SELECT param_no, sort, caption, value
            FROM tb_systemparam
            WHERE group_key = 'NOTIFICATION'
            ORDER BY sort
        """))

        params = result.fetchall()

        if len(params) > 0:
            print("✅ 系統參數已設定：")
            for param in params:
                print(f"   [{param.param_no}] {param.caption}: {param.value} (排序: {param.sort})")
            db.close()
            return True
        else:
            print("❌ 尚未設定通知系統參數")
            print("   請執行 update_for_notification.sql 插入參數")
            db.close()
            return False

    except Exception as e:
        print(f"❌ 檢查失敗：{str(e)}")
        if db:
            db.close()
        return False


def test_pending_notifications():
    """查詢待發送通知詳情"""
    print()
    print("=" * 60)
    print("🔍 查詢待發送通知詳情")
    print("=" * 60)

    try:
        db = SessionLocal()

        result = db.execute(text("""
            SELECT
                user_no, account, email, membership_level,
                video_title, channel_title,
                summary_status,
                CASE WHEN summary_content IS NOT NULL THEN '有' ELSE '無' END as has_summary
            FROM vw_PendingNotifications
            LIMIT 5
        """))

        notifications = result.fetchall()

        if len(notifications) > 0:
            print(f"📋 待發送通知清單（前 5 筆）：")
            print()
            for i, notif in enumerate(notifications, 1):
                print(f"   {i}. 使用者：{notif.account} (會員等級: {notif.membership_level})")
                print(f"      頻道：{notif.channel_title}")
                print(f"      影片：{notif.video_title}")
                print(f"      摘要：{notif.has_summary} (狀態: {notif.summary_status})")
                print()
        else:
            print("📭 目前沒有待發送的通知")
            print()
            print("💡 這可能是因為：")
            print("   1. 沒有新影片（24小時內）")
            print("   2. 所有影片都已發送過通知")
            print("   3. 使用者關閉了通知設定")

        db.close()
        return True

    except Exception as e:
        print(f"❌ 查詢失敗：{str(e)}")
        if db:
            db.close()
        return False


def test_send_notifications():
    """測試發送通知功能"""
    print()
    print("=" * 60)
    print("🔍 測試發送通知功能")
    print("=" * 60)

    try:
        print("⚠️  警告：這會實際發送 Email 給所有待通知的使用者！")
        choice = input("是否繼續？[y/N]: ").strip().lower()

        if choice != 'y':
            print("❌ 已取消")
            return False

        print()
        print("📤 開始發送通知...")

        db = SessionLocal()
        watcher = WatcherService(db)

        # 直接調用發送通知功能
        watcher._send_notifications_from_view()

        print("✅ 發送完成！請檢查 Log 確認結果")

        db.close()
        return True

    except Exception as e:
        print(f"❌ 發送失敗：{str(e)}")
        if db:
            db.close()
        return False


if __name__ == "__main__":
    print()
    print("🚀 開始測試通知系統")
    print()

    # 1. 測試資料庫連線
    if not test_database_connection():
        sys.exit(1)

    # 2. 檢查 View
    if not test_view_exists():
        sys.exit(1)

    # 3. 檢查系統參數
    if not test_system_params():
        sys.exit(1)

    # 4. 查詢待發送通知
    test_pending_notifications()

    # 5. 詢問是否要實際發送
    print()
    test_send_notifications()

    print()
    print("=" * 60)
    print("✅ 通知系統測試完成！")
    print("=" * 60)
    print()
