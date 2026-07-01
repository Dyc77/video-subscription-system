from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import multiprocessing

# Windows 平台需要設定 multiprocessing 啟動方法
if __name__ == "__main__":
    multiprocessing.set_start_method('spawn', force=True)

from app.core.config import settings
from app.api import video, channel, user, auth, config, line_webhook, public
from app.utils.scheduler import start_scheduler, shutdown_scheduler

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 完全禁用 SQLAlchemy 的詳細日誌
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

# 顯示 TEST_MODE 狀態
logger.info(f"🔧 TEST_MODE = {settings.TEST_MODE}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理
    """
    # 啟動時執行
    logger.info("啟動 VideoHub API...")
    start_scheduler()  # 啟動定時任務
    yield
    # 關閉時執行
    logger.info("關閉 VideoHub API...")
    shutdown_scheduler()  # 關閉定時任務


# 建立 FastAPI 應用程式
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI 影音摘要平台 API",
    lifespan=lifespan
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應該限制具體網域名稱
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(auth.router)  # 認證路由（登入）
app.include_router(video.router)
app.include_router(channel.router)
app.include_router(user.router)
app.include_router(config.router)  # 通知設定路由
app.include_router(line_webhook.router)  # LINE Webhook 路由
app.include_router(public.router)  # 公開 API 路由（不需登入）


@app.get("/")
async def root():
    """
    根路徑
    """
    return {
        "message": "Welcome to VideoHub API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """
    健康檢查端點（測試 API 是否回應）
    """
    import threading
    import time

    # 獲取活躍的子進程
    active_children = multiprocessing.active_children()

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "timestamp": time.time(),
        "active_threads": threading.active_count(),
        "thread_names": [t.name for t in threading.enumerate()],
        "active_processes": len(active_children),
        "process_info": [{"pid": p.pid, "name": p.name} for p in active_children]
    }


if __name__ == "__main__":
    import uvicorn
    import os

    # 從環境變數讀取 PORT，如果沒有則使用 8000
    port = int(os.getenv("PORT", 8000))

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=settings.DEBUG
    )
