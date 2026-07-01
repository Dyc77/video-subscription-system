"""
測試 Email 發送功能

這個腳本會：
1. 測試 SMTP 連線
2. 發送測試郵件
3. 顯示詳細的錯誤訊息（如果有）

使用方法：
    py backend/test_email.py
"""

import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.core.config import settings
from app.services.notification_service import notification_service


def test_smtp_connection():
    """測試 SMTP 連線"""
    print("=" * 60)
    print("📧 測試 Email 發送功能")
    print("=" * 60)
    print()

    # 顯示當前 SMTP 設定
    print("📝 當前 SMTP 設定:")
    print(f"   SMTP Server: {settings.SMTP_SERVER}")
    print(f"   SMTP Port: {settings.SMTP_PORT}")
    print(f"   SMTP User: {settings.SMTP_USER}")
    print(f"   From Email: {settings.FROM_EMAIL}")
    print(f"   SMTP Password: {'*' * len(settings.SMTP_PASSWORD) if settings.SMTP_PASSWORD else '(未設定)'}")
    print()

    # 檢查必要設定
    if not all([settings.SMTP_SERVER, settings.SMTP_PORT, settings.SMTP_USER,
                settings.SMTP_PASSWORD, settings.FROM_EMAIL]):
        print("❌ 錯誤：SMTP 設定不完整！")
        print()
        print("請在 .env 檔案中設定以下變數：")
        print("   SMTP_SERVER=smtp.gmail.com")
        print("   SMTP_PORT=587")
        print("   SMTP_USER=your-email@gmail.com")
        print("   SMTP_PASSWORD=your-app-password")
        print("   FROM_EMAIL=your-email@gmail.com")
        print()
        print("💡 如果使用 Gmail，請先啟用「應用程式密碼」：")
        print("   https://myaccount.google.com/apppasswords")
        return False

    # 測試發送郵件
    print("📤 正在發送測試郵件...")
    print()

    # 構建測試影片資料
    test_videos = [
        {
            "channel_title": "測試頻道 A",
            "video_title": "測試影片 1 - 這是一個測試標題",
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "summary": "這是一個測試摘要。這個功能用來測試 Email 通知系統是否正常運作。包含時間戳記連結等功能。" if test_with_summary() else None
        },
        {
            "channel_title": "測試頻道 B",
            "video_title": "測試影片 2 - 另一個測試",
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "summary": None
        }
    ]

    # 發送測試郵件
    try:
        success = notification_service.send_new_videos_notification(
            to_email=settings.SMTP_USER,  # 發給自己
            user_name="測試用戶",
            new_videos=test_videos,
            membership_level=1 if test_with_summary() else 0  # 測試會員等級
        )

        if success:
            print("✅ 測試郵件發送成功！")
            print()
            print(f"📬 請檢查您的信箱：{settings.SMTP_USER}")
            print("   如果沒收到，請檢查垃圾郵件資料夾")
            return True
        else:
            print("❌ 測試郵件發送失敗！")
            print("   請檢查上方的錯誤訊息")
            return False

    except Exception as e:
        print(f"❌ 發送失敗：{str(e)}")
        print()
        print("💡 常見問題排查：")
        print("   1. Gmail 用戶：請確認已啟用「應用程式密碼」")
        print("   2. 檢查防火牆是否阻擋了 SMTP 連線")
        print("   3. 確認 SMTP 伺服器和 Port 正確")
        print("   4. 確認帳號密碼正確")
        return False


def test_with_summary():
    """詢問是否測試包含摘要的郵件（付費會員功能）"""
    print("請選擇測試模式：")
    print("1. 免費會員模式（不含摘要）")
    print("2. 付費會員模式（包含 AI 摘要）")

    try:
        choice = input("請輸入 1 或 2 [預設: 2]: ").strip()
        return choice != "1"
    except:
        return True


if __name__ == "__main__":
    print()
    success = test_smtp_connection()
    print()
    print("=" * 60)

    if success:
        print("✅ Email 功能測試完成！")
    else:
        print("❌ Email 功能測試失敗，請修正後重試")

    print("=" * 60)
    print()
