"""
使用 Multiprocessing 測試 Watcher 掃描（模擬定時任務）

用途：
1. 測試 multiprocessing 是否能正常繞過 GIL
2. 模擬實際定時任務的執行方式
3. 驗證主程序不會被阻塞

使用方式：
    python test_watcher_multiprocess.py
"""
import sys
import os
import multiprocessing
import time

# Windows 平台需要設定 multiprocessing 啟動方法
if __name__ == "__main__":
    multiprocessing.set_start_method('spawn', force=True)

# 添加專案根目錄到路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import logging

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _scan_channels_in_process():
    """
    在獨立進程中掃描頻道（完全繞過 GIL）

    這個函數會在獨立進程中執行，不會阻塞主程序
    """
    # 必須在進程內部重新導入
    import logging
    from app.db.database import SessionLocal
    from app.services.watcher_service import WatcherService

    logger = logging.getLogger(__name__)
    process_id = os.getpid()

    logger.info(f"[Process-{process_id}] 🚀 開始掃描頻道...")

    db = SessionLocal()
    try:
        watcher = WatcherService(db)
        new_videos = watcher.scan_all_channels()
        logger.info(f"[Process-{process_id}] ✅ 掃描完成，發現 {new_videos} 個新影片")

    except Exception as e:
        logger.error(f"[Process-{process_id}] ❌ 掃描失敗: {str(e)}")

    finally:
        db.close()
        logger.info(f"[Process-{process_id}] 🏁 進程結束")


def main():
    """
    主函數：啟動獨立進程執行掃描
    """
    print("\n" + "=" * 70)
    print("🤖 Multiprocessing Watcher 測試工具")
    print("=" * 70)
    print("此工具會使用獨立進程執行掃描，模擬實際定時任務運作")
    print("主程序會立即返回，掃描在背景執行（不阻塞）")
    print("=" * 70 + "\n")

    input("按 Enter 開始測試...")

    print("\n[主程序] 正在啟動掃描進程...\n")

    # 建立獨立進程
    process = multiprocessing.Process(
        target=_scan_channels_in_process,
        daemon=True,
        name="WatcherScan-Test"
    )

    # 啟動進程
    start_time = time.time()
    process.start()

    print(f"[主程序] ✅ 掃描進程已啟動 (PID: {process.pid})")
    print(f"[主程序] 📝 進程名稱: {process.name}")
    print(f"[主程序] ⏱️  啟動耗時: {(time.time() - start_time)*1000:.2f} ms")
    print("\n" + "-" * 70)
    print("重要：主程序已經返回了！")
    print("這表示 API 不會被阻塞，可以繼續處理其他請求")
    print("-" * 70 + "\n")

    # 監控進程狀態
    print("正在監控背景進程狀態...\n")

    while process.is_alive():
        print(f"⏳ 背景進程仍在執行... (PID: {process.pid})")
        time.sleep(5)

    # 等待進程結束
    process.join(timeout=300)  # 最多等 5 分鐘

    if process.exitcode == 0:
        print("\n✅ 背景進程執行成功！")
    else:
        print(f"\n⚠️  背景進程退出碼: {process.exitcode}")

    print("\n" + "=" * 70)
    print("測試完成！")
    print("如果主程序立即返回，表示 multiprocessing 成功繞過 GIL")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
