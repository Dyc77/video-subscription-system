from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import YoutubeChannel, UserSubscription, User
from app.models.schemas import ChannelResponse, ChannelCreateByUrl, SubscriptionCreate, SubscriptionResponse
from app.services.youtube_service import youtube_service
from app.services.watcher_service import WatcherService
from app.utils.auth import get_current_user
from typing import List
import logging
import os
from multiprocessing import Process
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channel", tags=["channel"])


@router.get("/list", response_model=List[ChannelResponse])
async def get_channels(
    db: Session = Depends(get_db),
    status: int = None
):
    """
    獲取頻道列表

    - **status**: 可選，篩選頻道狀態 (0:停用, 1:啟用)
    """
    try:
        query = db.query(YoutubeChannel)

        if status is not None:
            query = query.filter(YoutubeChannel.channel_status == status)

        channels = query.order_by(YoutubeChannel.create_time.desc()).all()

        return channels

    except Exception as e:
        logger.error(f"獲取頻道列表失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(
    channel_id: str,
    db: Session = Depends(get_db)
):
    """
    獲取單一頻道資訊

    - **channel_id**: YouTube 頻道 ID
    """
    try:
        channel = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_id == channel_id
        ).first()

        if not channel:
            raise HTTPException(status_code=404, detail="頻道不存在")

        return channel

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取頻道資訊失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/add", response_model=ChannelResponse)
async def add_channel(
    request: ChannelCreateByUrl,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    新增頻道（使用 YouTube 頻道網址，零 API Quota）

    支援的網址格式：
    - https://www.youtube.com/@channelhandle
    - https://www.youtube.com/channel/UCxxxxxx
    - https://www.youtube.com/c/CustomName
    - https://www.youtube.com/user/username

    - **channel_url**: YouTube 頻道網址

    注意：
    1. 頻道是全域共用的，如果頻道已存在會直接返回
    2. 新增頻道後會自動訂閱該頻道
    """
    try:
        # 1. 使用 YouTube 服務解析頻道資訊（零 Quota）
        logger.info(f"用戶 {current_user.user_no} 正在新增頻道: {request.channel_url}")
        channel_info = youtube_service.get_channel_info_from_url(request.channel_url)

        # 2. 檢查頻道是否已存在
        existing_channel = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_id == channel_info['channel_id']
        ).first()

        if existing_channel:
            logger.info(f"頻道已存在: {existing_channel.title} ({existing_channel.channel_id})")

            # 檢查用戶是否已訂閱
            existing_subscription = db.query(UserSubscription).filter(
                UserSubscription.user_no == current_user.user_no,
                UserSubscription.channel_no == existing_channel.channel_no
            ).first()

            if existing_subscription:
                # 用戶已訂閱此頻道
                logger.info(f"用戶 {current_user.user_no} 已經訂閱頻道 {existing_channel.title}")
                raise HTTPException(
                    status_code=409,
                    detail=f"您已經訂閱過「{existing_channel.title}」了"
                )
            else:
                # 頻道存在但用戶未訂閱,自動訂閱
                new_subscription = UserSubscription(
                    user_no=current_user.user_no,
                    channel_no=existing_channel.channel_no,
                    is_notification_enabled=1
                )
                db.add(new_subscription)
                db.commit()
                logger.info(f"用戶 {current_user.user_no} 訂閱了已存在的頻道 {existing_channel.title}")

            return existing_channel

        # 3. 創建新頻道
        new_channel = YoutubeChannel(
            channel_id=channel_info['channel_id'],
            title=channel_info['title'],
            thumbnail_url=channel_info['thumbnail_url'],
            rss_url=channel_info['rss_url'],
            channel_status=1,
            last_check_time=None
        )

        db.add(new_channel)
        db.commit()
        db.refresh(new_channel)

        logger.info(f"成功新增頻道: {new_channel.title} ({new_channel.channel_id})")

        # 4. 自動訂閱該頻道
        new_subscription = UserSubscription(
            user_no=current_user.user_no,
            channel_no=new_channel.channel_no,
            is_notification_enabled=1
        )
        db.add(new_subscription)
        db.commit()

        logger.info(f"用戶 {current_user.user_no} 已自動訂閱頻道 {new_channel.title}")

        return new_channel

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"新增頻道失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"新增頻道失敗: {str(e)}")


@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe_channel(
    request: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    訂閱頻道

    - **channel_id**: YouTube 頻道 ID

    注意：如果頻道不存在，請先使用 /api/channel/add 新增頻道
    """
    try:
        # 1. 檢查頻道是否存在
        channel = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_id == request.channel_id
        ).first()

        if not channel:
            raise HTTPException(
                status_code=404,
                detail="頻道不存在，請先使用 /api/channel/add 新增頻道"
            )

        # 2. 檢查是否已訂閱
        existing_subscription = db.query(UserSubscription).filter(
            UserSubscription.user_no == current_user.user_no,
            UserSubscription.channel_no == channel.channel_no
        ).first()

        if existing_subscription:
            logger.info(f"用戶 {current_user.user_no} 已訂閱頻道 {channel.title}")
            return existing_subscription

        # 3. 創建訂閱
        new_subscription = UserSubscription(
            user_no=current_user.user_no,
            channel_no=channel.channel_no,
            is_notification_enabled=1
        )

        db.add(new_subscription)
        db.commit()
        db.refresh(new_subscription)

        logger.info(f"用戶 {current_user.user_no} 成功訂閱頻道 {channel.title}")

        return new_subscription

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"訂閱頻道失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"訂閱頻道失敗: {str(e)}")


@router.delete("/unsubscribe/{channel_id}")
async def unsubscribe_channel(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    取消訂閱頻道

    - **channel_id**: YouTube 頻道 ID
    """
    try:
        # 1. 查找頻道
        channel = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_id == channel_id
        ).first()

        if not channel:
            raise HTTPException(status_code=404, detail="頻道不存在")

        # 2. 查找訂閱記錄
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_no == current_user.user_no,
            UserSubscription.channel_no == channel.channel_no
        ).first()

        if not subscription:
            raise HTTPException(status_code=404, detail="未訂閱該頻道")

        # 3. 刪除訂閱
        db.delete(subscription)
        db.commit()

        logger.info(f"用戶 {current_user.user_no} 已取消訂閱頻道 {channel.title}")

        return {"message": "取消訂閱成功", "channel_id": channel_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"取消訂閱失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"取消訂閱失敗: {str(e)}")


@router.get("/subscriptions/list")
async def get_my_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取我的訂閱列表（包含通知設定）
    """
    try:
        # 查詢用戶訂閱的所有頻道及通知設定
        results = db.query(
            YoutubeChannel,
            UserSubscription.is_notification_enabled
        ).join(
            UserSubscription,
            YoutubeChannel.channel_no == UserSubscription.channel_no
        ).filter(
            UserSubscription.user_no == current_user.user_no
        ).order_by(YoutubeChannel.create_time.desc()).all()

        # 構建返回數據
        subscriptions = []
        for channel, is_notification_enabled in results:
            subscriptions.append({
                "channel_no": channel.channel_no,
                "channel_id": channel.channel_id,
                "title": channel.title,
                "thumbnail_url": channel.thumbnail_url,
                "channel_status": channel.channel_status,
                "create_time": channel.create_time,
                "is_notification_enabled": is_notification_enabled
            })

        return subscriptions

    except Exception as e:
        logger.error(f"獲取訂閱列表失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取訂閱列表失敗: {str(e)}")


@router.post("/scan/all")
async def scan_all_subscriptions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手動觸發 RSS 掃描，抓取所有已訂閱頻道的影片（使用 Multiprocessing，不阻塞 API）

    此 API 會在背景獨立進程中掃描當前用戶訂閱的所有頻道，抓取最新影片並存入資料庫

    使用方式：
    1. 呼叫此 API，會立即返回
    2. 背景進程會自動掃描所有訂閱頻道（RSS + VIP 摘要 + 通知）
    3. 主 API 完全不受影響，可以繼續處理其他請求
    """
    try:
        user_no = current_user.user_no
        logger.info(f"用戶 {user_no} 觸發批量掃描訂閱頻道")

        # 檢查是否有訂閱頻道
        subscribed_count = db.query(YoutubeChannel).join(
            UserSubscription,
            YoutubeChannel.channel_no == UserSubscription.channel_no
        ).filter(
            UserSubscription.user_no == user_no,
            YoutubeChannel.channel_status == 1
        ).count()

        if subscribed_count == 0:
            logger.warning(f"用戶 {user_no} 沒有訂閱任何已啟用的頻道")
            return {
                "message": "您還沒有訂閱任何頻道",
                "total_channels": 0,
                "status": "no_channels"
            }

        # 啟動獨立進程執行掃描
        process = Process(
            target=_background_scan_user_subscriptions,
            args=(user_no,),
            daemon=True,
            name=f"UserScan-{user_no}"
        )

        process.start()

        logger.info(f"✅ 掃描進程已啟動 (PID: {process.pid})")

        return {
            "message": f"掃描已在背景啟動（共 {subscribed_count} 個頻道）",
            "total_channels": subscribed_count,
            "process_id": process.pid,
            "process_name": process.name,
            "note": "主 API 已立即返回，掃描在獨立進程執行",
            "status": "started"
        }

    except Exception as e:
        logger.error(f"啟動批量掃描失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"啟動批量掃描失敗: {str(e)}")


@router.post("/scan/{channel_id}")
async def scan_channel_videos(
    channel_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    手動觸發 RSS 掃描，抓取指定頻道的影片（使用 Multiprocessing，不阻塞 API）

    - **channel_id**: YouTube 頻道 ID

    此 API 會在背景獨立進程中從 RSS feed 抓取該頻道的最新影片並存入資料庫

    使用方式：
    1. 呼叫此 API，會立即返回
    2. 背景進程會自動掃描指定頻道（RSS + VIP 摘要 + 通知）
    3. 主 API 完全不受影響，可以繼續處理其他請求
    """
    try:
        # 1. 檢查頻道是否存在且用戶已訂閱
        channel = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_id == channel_id
        ).first()

        if not channel:
            raise HTTPException(status_code=404, detail="頻道不存在")

        # 檢查用戶是否訂閱此頻道
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_no == current_user.user_no,
            UserSubscription.channel_no == channel.channel_no
        ).first()

        if not subscription:
            raise HTTPException(status_code=403, detail="您尚未訂閱此頻道")

        logger.info(f"用戶 {current_user.user_no} 觸發掃描頻道 {channel.title}")

        # 2. 啟動獨立進程執行掃描
        process = Process(
            target=_background_scan_single_channel,
            args=(channel_id,),
            daemon=True,
            name=f"ChannelScan-{channel_id[:8]}"
        )

        process.start()

        logger.info(f"✅ 掃描進程已啟動 (PID: {process.pid})")

        return {
            "message": f"掃描已在背景啟動",
            "channel_id": channel_id,
            "channel_title": channel.title,
            "process_id": process.pid,
            "process_name": process.name,
            "note": "主 API 已立即返回，掃描在獨立進程執行",
            "status": "started"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"啟動掃描頻道失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"啟動掃描頻道失敗: {str(e)}")


@router.put("/notification/{channel_id}")
async def toggle_channel_notification(
    channel_id: str,
    enabled: bool = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    切換頻道通知開關

    - **channel_id**: YouTube 頻道 ID
    - **enabled**: True 開啟，False 關閉

    Headers:
    - **Authorization**: Bearer {JWT_TOKEN}
    """
    try:
        # 1. 查找頻道
        channel = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_id == channel_id
        ).first()

        if not channel:
            raise HTTPException(status_code=404, detail="頻道不存在")

        # 2. 查找訂閱記錄
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_no == current_user.user_no,
            UserSubscription.channel_no == channel.channel_no
        ).first()

        if not subscription:
            raise HTTPException(status_code=404, detail="未訂閱該頻道")

        # 3. 更新通知設定
        subscription.is_notification_enabled = 1 if enabled else 0
        db.commit()

        logger.info(f"用戶 {current_user.user_no} {'開啟' if enabled else '關閉'}了頻道 {channel.title} 的通知")

        return {
            "message": f"已{'開啟' if enabled else '關閉'}通知",
            "channel_id": channel_id,
            "is_notification_enabled": subscription.is_notification_enabled
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新通知設定失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新通知設定失敗: {str(e)}")


def _background_scan_all_channels():
    """
    背景進程任務：掃描所有頻道（完全繞過 GIL）

    這個函數會在獨立進程中執行，不會阻塞主 API
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

    logger.info(f"[Process-{process_id}] 🚀 開始掃描所有頻道...")

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


def _background_scan_user_subscriptions(user_no: int):
    """
    背景進程任務：掃描用戶訂閱的所有頻道（完全繞過 GIL）

    Args:
        user_no: 使用者編號
    """
    # 必須在進程內部重新導入
    import logging
    from app.db.database import SessionLocal
    from app.services.watcher_service import WatcherService
    from app.models.models import YoutubeChannel, UserSubscription

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

    logger.info(f"[Process-{process_id}] 🚀 開始掃描用戶 {user_no} 的訂閱頻道...")

    db = SessionLocal()
    try:
        # 獲取用戶訂閱的所有頻道
        subscribed_channels = db.query(YoutubeChannel).join(
            UserSubscription,
            YoutubeChannel.channel_no == UserSubscription.channel_no
        ).filter(
            UserSubscription.user_no == user_no,
            YoutubeChannel.channel_status == 1
        ).all()

        logger.info(f"[Process-{process_id}] 找到 {len(subscribed_channels)} 個訂閱頻道")

        if not subscribed_channels:
            logger.info(f"[Process-{process_id}] 用戶沒有訂閱任何頻道")
            return

        # 掃描所有頻道
        watcher = WatcherService(db)
        total_new_videos = 0

        for channel in subscribed_channels:
            try:
                new_videos_count = watcher._scan_channel(channel)
                total_new_videos += new_videos_count
                logger.info(f"[Process-{process_id}] 頻道 {channel.title} 掃描完成，發現 {new_videos_count} 個新影片")
            except Exception as e:
                logger.error(f"[Process-{process_id}] 掃描頻道 {channel.title} 失敗: {str(e)}")

        logger.info(f"[Process-{process_id}] ✅ 批量掃描完成，共 {total_new_videos} 個新影片")

        # 如果有新影片，觸發通知
        if total_new_videos > 0:
            try:
                watcher._send_notifications_from_view()
                logger.info(f"[Process-{process_id}] 已觸發通知檢查")
            except Exception as e:
                logger.error(f"[Process-{process_id}] 觸發通知失敗: {str(e)}")

    except Exception as e:
        logger.error(f"[Process-{process_id}] ❌ 批量掃描失敗: {str(e)}")

    finally:
        db.close()
        logger.info(f"[Process-{process_id}] 🏁 進程結束")


def _background_scan_single_channel(channel_id: str):
    """
    背景進程任務：掃描單一頻道（完全繞過 GIL）

    Args:
        channel_id: YouTube 頻道 ID
    """
    # 必須在進程內部重新導入
    import logging
    from app.db.database import SessionLocal
    from app.services.watcher_service import WatcherService
    from app.models.models import YoutubeChannel

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

    logger.info(f"[Process-{process_id}] 🚀 開始掃描頻道 {channel_id}...")

    db = SessionLocal()
    try:
        # 查找頻道
        channel = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_id == channel_id
        ).first()

        if not channel:
            logger.error(f"[Process-{process_id}] 找不到頻道 {channel_id}")
            return

        # 掃描頻道
        watcher = WatcherService(db)
        new_videos_count = watcher._scan_channel(channel)

        logger.info(f"[Process-{process_id}] ✅ 掃描完成，發現 {new_videos_count} 個新影片")

        # 如果有新影片，觸發通知
        if new_videos_count > 0:
            try:
                watcher._send_notifications_from_view()
                logger.info(f"[Process-{process_id}] 已觸發通知檢查")
            except Exception as e:
                logger.error(f"[Process-{process_id}] 觸發通知失敗: {str(e)}")

    except Exception as e:
        logger.error(f"[Process-{process_id}] ❌ 掃描失敗: {str(e)}")

    finally:
        db.close()
        logger.info(f"[Process-{process_id}] 🏁 進程結束")


@router.post("/test/scan-background")
async def test_scan_in_background(
    current_user: User = Depends(get_current_user)
):
    """
    【測試端點】使用 Multiprocessing 在背景掃描所有頻道

    用途：測試 API 是否在掃描期間保持可用（不被阻塞）

    使用方式：
    1. 呼叫此 API，會立即返回（< 100ms）
    2. 背景進程會獨立執行掃描（RSS 抓取 + VIP 摘要 + 通知）
    3. 同時測試其他 API（如 /api/video/list）應該正常回應

    如果其他 API 在掃描期間仍能快速回應，表示 multiprocessing 成功繞過 GIL！
    """
    try:
        logger.info(f"用戶 {current_user.user_no} 觸發背景掃描測試")

        # 啟動獨立進程執行掃描
        process = Process(
            target=_background_scan_all_channels,
            daemon=True,
            name="TestScan-Background"
        )

        process.start()

        logger.info(f"✅ 掃描進程已啟動 (PID: {process.pid})")

        return {
            "message": "掃描已在背景啟動（使用 Multiprocessing）",
            "process_id": process.pid,
            "process_name": process.name,
            "note": "主 API 已立即返回，掃描在獨立進程執行",
            "test_instructions": [
                "1. 此 API 應該立即返回（< 100ms）",
                "2. 背景進程正在執行掃描（RSS + VIP 摘要 + 通知）",
                "3. 請立即測試其他 API（如 /api/video/list 或 /health）",
                "4. 如果其他 API 正常回應，表示 multiprocessing 成功！"
            ]
        }

    except Exception as e:
        logger.error(f"啟動背景掃描失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"啟動背景掃描失敗: {str(e)}")
