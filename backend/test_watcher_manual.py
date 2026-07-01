"""
手動觸發 Watcher 掃描（測試用）

用途：
1. 立即測試 multiprocessing 是否正常運作
2. 不用等 15 分鐘定時任務
3. 驗證 API 是否在掃描期間保持可用

使用方式：
    python test_watcher_manual.py
"""
import sys
import os
import multiprocessing

# Windows 平台需要設定 multiprocessing 啟動方法
if __name__ == "__main__":
    multiprocessing.set_start_method('spawn', force=True)

# 添加專案根目錄到路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging
from app.db.database import SessionLocal
from app.services.watcher_service import WatcherService

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_watcher_scan():
    """
    執行 Watcher 掃描

    這個函數會：
    1. 掃描所有啟用的頻道
    2. 檢查是否有新影片
    3. 為 VIP 會員自動生成摘要
    4. 發送 Email/LINE 通知
    """
    logger.info("=" * 60)
    logger.info("🔍 手動觸發 Watcher 掃描開始")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        watcher = WatcherService(db)

        print("\n開始掃描所有頻道...\n")
        new_videos_count = watcher.scan_all_channels()

        print(f"\n✅ 掃描完成！")
        print(f"📊 發現 {new_videos_count} 部新影片")
        print(f"📧 通知已發送（如有需要）\n")

        logger.info("=" * 60)
        logger.info(f"✅ Watcher 掃描完成，發現 {new_videos_count} 部新影片")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 掃描失敗: {str(e)}")
        print(f"\n❌ 掃描失敗: {str(e)}\n")

    finally:
        db.close()
        logger.info("資料庫連線已關閉")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🤖 手動 Watcher 掃描工具")
    print("=" * 60)
    print("此工具會立即執行一次完整的頻道掃描")
    print("包含：RSS 抓取 → VIP 摘要生成 → 通知發送")
    print("=" * 60 + "\n")

    input("按 Enter 開始掃描...")

    run_watcher_scan()

    print("\n" + "=" * 60)
    print("掃描工具執行完畢")
    print("=" * 60 + "\n")
