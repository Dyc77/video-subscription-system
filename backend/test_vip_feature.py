"""
測試 VIP 優先通道功能

這個腳本會：
1. 檢查資料庫中的會員等級
2. 測試 VIP 檢查功能
3. 模擬 VIP 自動摘要流程

使用方法：
    py backend/test_vip_feature.py
"""

import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.db.database import SessionLocal
from app.models.models import User, UserSubscription, YoutubeChannel, YoutubeVideo
from app.services.watcher_service import WatcherService
from sqlalchemy import text
import logging

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_membership_levels():
    """檢查資料庫中的會員等級分佈"""
    print("=" * 60)
    print("🔍 檢查會員等級分佈")
    print("=" * 60)

    try:
        db = SessionLocal()

        # 查詢會員等級統計
        result = db.execute(text("""
            SELECT
                membership_level,
                CASE
                    WHEN membership_level = 0 THEN '免費會員'
                    WHEN membership_level = 1 THEN '高級會員 (VIP)'
                    ELSE '未知'
                END as level_name,
                COUNT(*) as count
            FROM tb_user
            WHERE user_status = 1
            GROUP BY membership_level
            ORDER BY membership_level
        """))

        levels = result.fetchall()

        if len(levels) > 0:
            print("📊 會員分佈：")
            for level in levels:
                print(f"   {level.level_name}: {level.count} 人")
        else:
            print("❌ 資料庫中沒有使用者")

        db.close()
        return len(levels) > 0

    except Exception as e:
        print(f"❌ 檢查失敗：{str(e)}")
        if db:
            db.close()
        return False


def test_vip_channels():
    """檢查哪些頻道有 VIP 訂閱"""
    print()
    print("=" * 60)
    print("🔍 檢查 VIP 訂閱的頻道")
    print("=" * 60)

    try:
        db = SessionLocal()

        # 查詢有 VIP 訂閱的頻道
        result = db.execute(text("""
            SELECT
                c.channel_no,
                c.title as channel_title,
                COUNT(DISTINCT CASE WHEN u.membership_level = 1 THEN u.user_no END) as vip_count,
                COUNT(DISTINCT CASE WHEN u.membership_level = 0 THEN u.user_no END) as free_count
            FROM tb_youtubechannel c
            JOIN tb_usersubscription us ON c.channel_no = us.channel_no
            JOIN tb_user u ON us.user_no = u.user_no
            WHERE c.channel_status = 1
            GROUP BY c.channel_no, c.title
            HAVING vip_count > 0
            ORDER BY vip_count DESC
        """))

        vip_channels = result.fetchall()

        if len(vip_channels) > 0:
            print(f"💎 找到 {len(vip_channels)} 個有 VIP 訂閱的頻道：")
            print()
            for i, channel in enumerate(vip_channels, 1):
                print(f"   {i}. {channel.channel_title}")
                print(f"      VIP 訂閱數: {channel.vip_count}")
                print(f"      免費訂閱數: {channel.free_count}")
                print()
        else:
            print("📭 目前沒有頻道有 VIP 訂閱")
            print()
            print("💡 建議：")
            print("   1. 將某個使用者升級為 VIP (membership_level = 1)")
            print("   2. 或新增一個 VIP 使用者")

        db.close()
        return len(vip_channels) > 0

    except Exception as e:
        print(f"❌ 檢查失敗：{str(e)}")
        if db:
            db.close()
        return False


def test_watcher_vip_check():
    """測試 WatcherService 的 VIP 檢查功能"""
    print()
    print("=" * 60)
    print("🔍 測試 VIP 檢查功能")
    print("=" * 60)

    try:
        db = SessionLocal()
        watcher = WatcherService(db)

        # 獲取所有頻道
        channels = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_status == 1
        ).limit(5).all()

        if len(channels) == 0:
            print("❌ 資料庫中沒有頻道")
            db.close()
            return False

        print(f"📋 測試前 {len(channels)} 個頻道的 VIP 狀態：")
        print()

        for channel in channels:
            has_vip = watcher._check_if_channel_has_vip(channel.channel_no)
            status = "💎 有 VIP" if has_vip else "💤 無 VIP"
            print(f"   {status} - {channel.title}")

        db.close()
        return True

    except Exception as e:
        print(f"❌ 測試失敗：{str(e)}")
        if db:
            db.close()
        return False


def test_upgrade_user_to_vip():
    """提供互動式升級使用者為 VIP"""
    print()
    print("=" * 60)
    print("🔧 升級使用者為 VIP")
    print("=" * 60)

    try:
        db = SessionLocal()

        # 查詢所有使用者
        users = db.query(User).filter(User.user_status == 1).all()

        if len(users) == 0:
            print("❌ 資料庫中沒有使用者")
            db.close()
            return False

        print("📋 現有使用者：")
        for i, user in enumerate(users, 1):
            level_name = "VIP" if user.membership_level == 1 else "免費"
            print(f"   {i}. {user.account} ({level_name})")

        print()
        choice = input("要升級哪位使用者為 VIP？輸入編號 [Enter 跳過]: ").strip()

        if not choice:
            print("⏭️ 跳過升級")
            db.close()
            return True

        try:
            index = int(choice) - 1
            if 0 <= index < len(users):
                user = users[index]
                user.membership_level = 1
                db.commit()

                print(f"✅ {user.account} 已升級為 VIP！")
                db.close()
                return True
            else:
                print("❌ 無效的編號")
                db.close()
                return False

        except ValueError:
            print("❌ 請輸入數字")
            db.close()
            return False

    except Exception as e:
        print(f"❌ 升級失敗：{str(e)}")
        if db:
            db.rollback()
            db.close()
        return False


def show_summary():
    """顯示系統摘要統計"""
    print()
    print("=" * 60)
    print("📊 系統統計")
    print("=" * 60)

    try:
        db = SessionLocal()

        # 統計資訊
        result = db.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM tb_user WHERE user_status = 1 AND membership_level = 1) as vip_users,
                (SELECT COUNT(*) FROM tb_user WHERE user_status = 1 AND membership_level = 0) as free_users,
                (SELECT COUNT(DISTINCT c.channel_no)
                 FROM tb_youtubechannel c
                 JOIN tb_usersubscription us ON c.channel_no = us.channel_no
                 JOIN tb_user u ON us.user_no = u.user_no
                 WHERE u.membership_level = 1) as vip_channels,
                (SELECT COUNT(*) FROM tb_youtubevideo WHERE summary_status = 2) as videos_with_summary
        """))

        stats = result.fetchone()

        print(f"👥 使用者：")
        print(f"   VIP 會員: {stats.vip_users} 人")
        print(f"   免費會員: {stats.free_users} 人")
        print()
        print(f"📺 頻道：")
        print(f"   有 VIP 訂閱的頻道: {stats.vip_channels} 個")
        print()
        print(f"🎬 影片：")
        print(f"   已生成摘要的影片: {stats.videos_with_summary} 部")

        db.close()
        return True

    except Exception as e:
        print(f"❌ 統計失敗：{str(e)}")
        if db:
            db.close()
        return False


if __name__ == "__main__":
    print()
    print("🚀 開始測試 VIP 優先通道功能")
    print()

    # 1. 檢查會員等級
    test_membership_levels()

    # 2. 檢查 VIP 頻道
    test_vip_channels()

    # 3. 測試 VIP 檢查功能
    test_watcher_vip_check()

    # 4. 提供升級功能
    test_upgrade_user_to_vip()

    # 5. 顯示統計
    show_summary()

    print()
    print("=" * 60)
    print("✅ VIP 功能測試完成！")
    print("=" * 60)
    print()
    print("💡 提示：")
    print("   - VIP 會員訂閱的頻道，新影片會自動生成摘要")
    print("   - 免費會員訂閱的頻道，需要手動點擊才會生成")
    print("   - 使用 test_notification_system.py 測試完整通知流程")
    print()
