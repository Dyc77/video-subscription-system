"""
測試通知發送記錄功能
檢查 tb_NotificationLog 表是否正確寫入
"""
from app.db.database import get_db
from app.services.watcher_service import WatcherService
from sqlalchemy import text

def test_notification_log():
    print("=" * 60)
    print("測試通知發送記錄功能")
    print("=" * 60)

    # 1. 建立資料庫連接
    db = next(get_db())

    try:
        # 2. 檢查 vw_PendingNotifications View 內容
        print("\n【步驟 1】檢查待發送通知清單...")
        query = text("""
            SELECT
                user_no, account, email,
                video_no, video_title,
                channel_no, channel_title
            FROM vw_PendingNotifications
            LIMIT 5
        """)
        result = db.execute(query)
        pending = result.fetchall()

        if pending:
            print(f"✅ 找到 {len(pending)} 筆待發送通知")
            for row in pending:
                print(f"   - 使用者 {row.user_no} ({row.account})")
                print(f"     頻道: {row.channel_title}")
                print(f"     影片: {row.video_title}")
        else:
            print("⚠️  沒有待發送的通知")
            print("   可能原因:")
            print("   1. 沒有新影片（24小時內）")
            print("   2. 通知已發送過")
            print("   3. 通知開關關閉")

        # 3. 檢查 tb_NotificationLog 表內容
        print("\n【步驟 2】檢查通知記錄表...")
        query = text("""
            SELECT
                log_id, user_no, video_no, channel_no,
                send_method, send_time, is_success
            FROM tb_NotificationLog
            ORDER BY send_time DESC
            LIMIT 10
        """)
        result = db.execute(query)
        logs = result.fetchall()

        if logs:
            print(f"✅ 找到 {len(logs)} 筆通知記錄")
            for log in logs:
                status = "成功" if log.is_success == 1 else "失敗"
                print(f"   - [ID:{log.log_id}] 使用者 {log.user_no}, 影片 {log.video_no}")
                print(f"     發送方式: {log.send_method}, 狀態: {status}")
                print(f"     發送時間: {log.send_time}")
        else:
            print("⚠️  通知記錄表是空的")
            print("   這表示系統還沒有發送過任何通知")

        # 4. 手動執行掃描並發送通知
        print("\n【步驟 3】執行頻道掃描並發送通知...")
        watcher = WatcherService(db)
        total_new_videos = watcher.scan_all_channels()
        print(f"✅ 掃描完成，發現 {total_new_videos} 部新影片")

        # 5. 再次檢查通知記錄
        print("\n【步驟 4】再次檢查通知記錄表...")
        result = db.execute(query)
        logs_after = result.fetchall()

        if len(logs_after) > len(logs):
            new_logs = len(logs_after) - len(logs)
            print(f"✅ 成功！新增了 {new_logs} 筆通知記錄")
            print("\n最新的通知記錄:")
            for log in logs_after[:5]:
                status = "成功" if log.is_success == 1 else "失敗"
                print(f"   - [ID:{log.log_id}] 使用者 {log.user_no}, 影片 {log.video_no}")
                print(f"     發送方式: {log.send_method}, 狀態: {status}")
                print(f"     發送時間: {log.send_time}")
        else:
            print("⚠️  沒有新增通知記錄")
            print("   可能原因:")
            print("   1. 沒有符合條件的新影片")
            print("   2. SMTP 設定未正確配置，Email 發送失敗")
            print("   3. 通知開關關閉")

    except Exception as e:
        print(f"\n❌ 測試過程發生錯誤: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)

if __name__ == "__main__":
    test_notification_log()
