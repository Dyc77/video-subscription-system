"""
快速启动脚本
"""
import uvicorn
import multiprocessing
import os
from app.core.config import settings

if __name__ == "__main__":
    # Windows 平台需要設定 multiprocessing 啟動方法
    multiprocessing.set_start_method('spawn', force=True)

    # 從環境變數讀取 PORT，如果沒有則使用 8000
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG,
        log_level="info"
    )
