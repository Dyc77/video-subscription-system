from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.config import settings
import logging
import os
from multiprocessing import Process

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def _scan_channels_in_process():
    """
    在獨立進程中掃描頻道（真正的工作函數，繞過 GIL）
    """
    # 必須在進程內部重新導入
    import logging
    from app.db.database import SessionLocal
    from app.services.watcher_service import WatcherService

    # 完全禁用 SQLAlchemy 日誌
    logging.getLogger('sqlalchemy').setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy').propagate = False
    logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy.engine').propagate = False
    logging.getLogger('sqlalchemy.engine.Engine').setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy.engine.Engine').propagate = False
    logging.getLogger('sqlalchemy.pool').setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy.pool').propagate = False
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy.dialects').propagate = False
    logging.getLogger('sqlalchemy.orm').setLevel(logging.ERROR)
    logging.getLogger('sqlalchemy.orm').propagate = False

    logger = logging.getLogger(__name__)
    process_id = os.getpid()
    logger.info(f"[Process-{process_id}] 開始掃描頻道...")

    db = SessionLocal()
    try:
        watcher = WatcherService(db)
        new_videos = watcher.scan_all_channels()
        logger.info(f"[Process-{process_id}] 掃描完成，發現 {new_videos} 個新影片")

    except Exception as e:
        logger.error(f"[Process-{process_id}] 掃描失敗: {str(e)}")

    finally:
        db.close()
        logger.info(f"[Process-{process_id}] 進程結束")


def scan_channels_job():
    """
    定時任務觸發器：啟動獨立進程掃描頻道

    這個函數會立即返回，實際工作在獨立進程中執行，不阻塞主程序（繞過 GIL）
    """
    process = Process(
        target=_scan_channels_in_process,
        daemon=True,
        name=f"WatcherScan"
    )
    process.start()
    logger.info(f"已啟動掃描進程 (PID: {process.pid})")


def start_scheduler():
    """
    啟動調度器
    """
    # 添加定時任務：每15分鐘執行一次
    scheduler.add_job(
        scan_channels_job,
        trigger=IntervalTrigger(minutes=settings.WATCHER_INTERVAL_MINUTES),
        id="scan_channels",
        name="掃描 YouTube 頻道新影片",
        replace_existing=True
    )

    scheduler.start()
    logger.info(f"調度器已啟動，每 {settings.WATCHER_INTERVAL_MINUTES} 分鐘掃描一次頻道")


def shutdown_scheduler():
    """
    關閉調度器
    """
    scheduler.shutdown()
    logger.info("調度器已關閉")
