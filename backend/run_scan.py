"""
獨立掃描腳本 — 供 Windows 工作排程器呼叫

執行一次「掃描頻道 + 發送通知」後立即結束，
不啟動 Web 伺服器、不需要 APScheduler。
排程間隔改由 Windows 工作排程器控制。
"""
import logging
import sys
from datetime import datetime

# --- 設定 logging（同時輸出到終端機與 scan.log）---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("scan.log", encoding="utf-8"),
    ],
)

# 關閉 SQLAlchemy 的雜訊 log
for _name in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.pool", "sqlalchemy.orm"):
    logging.getLogger(_name).setLevel(logging.ERROR)

logger = logging.getLogger("run_scan")


def main():
    # 在函式內 import，確保 logging 已先設定好
    from app.db.database import SessionLocal
    from app.services.watcher_service import WatcherService

    logger.info("=" * 60)
    logger.info(f"開始掃描 ({datetime.now():%Y-%m-%d %H:%M:%S})")

    db = SessionLocal()
    try:
        watcher = WatcherService(db)
        new_videos = watcher.scan_all_channels()
        logger.info(f"掃描完成，發現 {new_videos} 個新影片")
    except Exception as e:
        logger.exception(f"掃描失敗: {e}")
        sys.exit(1)  # 回傳非 0，工作排程器會記錄為失敗
    finally:
        db.close()
        logger.info("本次任務結束")


if __name__ == "__main__":
    main()
