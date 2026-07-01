from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db
from app.models.schemas import SummaryRequest, SummaryResponse, VideoResponse, NoteRequest
from app.models.models import User, UserVideoAction, YoutubeVideo
from app.services.gemini_service import gemini_service
from app.utils.auth import get_current_user, get_current_active_premium_user
from typing import List
import logging
import os
from multiprocessing import Process

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/video", tags=["video"])


def _background_generate_summary(video_id: str, video_url: str):
    """
    背景進程任務：生成影片摘要

    在獨立進程中執行，完全不阻塞主 API 請求（繞過 GIL）

    Args:
        video_id: YouTube 影片 ID
        video_url: YouTube 影片 URL
    """
    # 必須在進程內部重新導入
    import logging
    from app.db.database import SessionLocal
    from app.models.models import YoutubeVideo
    from app.services.gemini_service import GeminiService
    from app.core.config import Settings

    # 子進程重新讀取設定（包含 TEST_MODE）
    child_settings = Settings()
    gemini_service = GeminiService(config_settings=child_settings)

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
    db_session = SessionLocal()

    try:
        logger.info(f"[Process-{process_id}] 開始生成摘要: {video_id}")

        # 調用 Gemini API
        summary_content = gemini_service.generate_summary_from_url(
            youtube_url=video_url,
            video_id=video_id
        )

        # 更新資料庫
        video = db_session.query(YoutubeVideo).filter(
            YoutubeVideo.video_id == video_id
        ).first()

        if video:
            video.summary_status = 2
            video.summary_content = summary_content
            db_session.commit()
            logger.info(f"[Process-{process_id}] 影片 {video_id} 摘要生成成功")
        else:
            logger.error(f"[Process-{process_id}] 找不到影片 {video_id}")

    except Exception as e:
        logger.error(f"[Process-{process_id}] 生成摘要失敗: {str(e)}")
        # 更新狀態為失敗
        try:
            video = db_session.query(YoutubeVideo).filter(
                YoutubeVideo.video_id == video_id
            ).first()
            if video:
                video.summary_status = 3
                db_session.commit()
        except Exception as update_error:
            logger.error(f"[Process-{process_id}] 更新失敗狀態時發生錯誤: {str(update_error)}")
    finally:
        db_session.close()
        logger.info(f"[Process-{process_id}] 背景任務結束")


@router.post("/summary", response_model=SummaryResponse)
async def generate_summary(
    request: SummaryRequest,
    current_user: User = Depends(get_current_active_premium_user),
    db: Session = Depends(get_db)
):
    """
    生成影片摘要 API (需要 Premium 會員權限)

    使用 Gemini 2.0 Flash Exp 直接分析 YouTube 影片 URL
    摘要生成在背景執行,不會阻塞 API 回應

    安全性: user_id 從 JWT token 中解析，不從前端傳入

    - **video_id**: YouTube 影片 ID

    Headers:
    - **Authorization**: Bearer {JWT_TOKEN}
    """
    try:
        # 使用從 JWT 解析出的 user_id，而不是前端傳入的
        user_id = current_user.user_no
        video_id = request.video_id

        logger.info(f"用戶 {user_id} 請求生成影片 {video_id} 的摘要")

        # 1. 查找或創建影片記錄
        video = db.query(YoutubeVideo).filter(
            YoutubeVideo.video_id == video_id
        ).first()

        if not video:
            raise HTTPException(status_code=404, detail="影片不存在")

        # 2. 檢查摘要狀態
        if video.summary_status == 2 and video.summary_content:
            # 摘要已完成，直接返回
            logger.info(f"影片 {video_id} 摘要已存在，返回快取內容")
            return SummaryResponse(
                video_id=video_id,
                summary_status=2,
                summary_content=video.summary_content,
                message="摘要已生成"
            )

        if video.summary_status == 1:
            # 正在處理中
            logger.info(f"影片 {video_id} 正在處理中")
            return SummaryResponse(
                video_id=video_id,
                summary_status=1,
                summary_content=None,
                message="AI 正在分析中，請稍後重試..."
            )

        if video.summary_status == 3:
            # 之前失敗過,重新嘗試
            logger.info(f"影片 {video_id} 之前失敗,重新嘗試生成")

        # 3. 標記為處理中
        video.summary_status = 1
        db.commit()

        # 4. 在獨立進程中生成摘要（完全不阻塞 API，繞過 GIL）
        process = Process(
            target=_background_generate_summary,
            args=(video_id, video.video_url),
            daemon=True,  # 設為 daemon，主程式退出時自動結束
            name=f"Summary-{video_id}"
        )
        process.start()

        logger.info(f"影片 {video_id} 已啟動獨立進程處理 (Process PID: {process.pid})")

        return SummaryResponse(
            video_id=video_id,
            summary_status=1,
            summary_content=None,
            message="摘要生成已啟動，請稍後重新整理查看結果"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成摘要失敗: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"生成摘要失敗: {str(e)}")


@router.get("/list", response_model=List[VideoResponse])
async def get_user_videos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    channel_id: str = None,
    limit: int = 50,
    offset: int = 0
):
    """
    獲取使用者訂閱頻道的影片列表

    Headers:
    - **Authorization**: Bearer {JWT_TOKEN}

    Query Parameters:
    - **channel_id**: 可選，篩選特定頻道的影片
    - **limit**: 返回數量限制 (預設50)
    - **offset**: 分頁偏移量 (預設0)
    """
    try:
        # 基礎查詢 - 加入 tb_uservideoaction 來獲取收藏狀態和筆記
        base_query = """
        SELECT
            v.video_no, v.video_id, v.title,
            v.thumbnail_url, v.video_url, v.published_at,
            v.channel_no, v.summary_status, v.summary_content, v.create_time,
            COALESCE(uva.is_favorite, 0) as is_favorite,
            uva.user_note
        FROM tb_youtubevideo v
        INNER JOIN tb_youtubechannel c ON v.channel_no = c.channel_no
        INNER JOIN tb_usersubscription us ON v.channel_no = us.channel_no
        LEFT JOIN tb_uservideoaction uva ON v.video_no = uva.video_no AND uva.user_no = :user_no
        WHERE us.user_no = :user_no
        """

        params = {
            "user_no": current_user.user_no,
            "limit": limit,
            "offset": offset
        }

        # 如果指定了頻道，添加頻道篩選
        if channel_id:
            base_query += " AND c.channel_id = :channel_id"
            params["channel_id"] = channel_id

        # 按發布日期倒序排列
        base_query += " ORDER BY v.published_at DESC LIMIT :limit OFFSET :offset"

        result = db.execute(text(base_query), params)

        videos = []
        for row in result:
            videos.append(VideoResponse(
                video_no=row.video_no,
                video_id=row.video_id,
                title=row.title,
                thumbnail_url=row.thumbnail_url,
                video_url=row.video_url,
                published_at=row.published_at,
                channel_no=row.channel_no,
                summary_status=row.summary_status,
                summary_content=row.summary_content,
                create_time=row.create_time,
                is_favorite=row.is_favorite,
                user_note=row.user_note
            ))

        return videos

    except Exception as e:
        logger.error(f"獲取影片列表失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video_detail(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取單一影片詳情

    安全性: 驗證使用者是否訂閱了該影片所屬的頻道

    Headers:
    - **Authorization**: Bearer {JWT_TOKEN}
    """
    try:
        # 查詢影片並驗證使用者是否有權存取 - 加入收藏狀態
        query = """
        SELECT v.*, COALESCE(uva.is_favorite, 0) as is_favorite
        FROM tb_youtubevideo v
        INNER JOIN tb_usersubscription us ON v.channel_no = us.channel_no
        LEFT JOIN tb_uservideoaction uva ON v.video_no = uva.video_no AND uva.user_no = :user_no
        WHERE v.video_id = :video_id AND us.user_no = :user_no
        """

        result = db.execute(text(query), {"video_id": video_id, "user_no": current_user.user_no})
        row = result.fetchone()

        if not row:
            raise HTTPException(
                status_code=404,
                detail="影片不存在或您未訂閱該頻道"
            )

        # 手動建立VideoResponse
        video = VideoResponse(
            video_no=row.video_no,
            video_id=row.video_id,
            title=row.title,
            thumbnail_url=row.thumbnail_url,
            video_url=row.video_url,
            published_at=row.published_at,
            channel_no=row.channel_no,
            summary_status=row.summary_status,
            summary_content=row.summary_content,
            create_time=row.create_time,
            is_favorite=row.is_favorite
        )

        return video

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取影片詳情失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/favorite/{video_id}")
async def toggle_favorite(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    切換影片收藏狀態

    - **video_id**: YouTube 影片 ID

    Headers:
    - **Authorization**: Bearer {JWT_TOKEN}
    """
    try:
        # 1. 查找影片
        video = db.query(YoutubeVideo).filter(
            YoutubeVideo.video_id == video_id
        ).first()

        if not video:
            raise HTTPException(status_code=404, detail="影片不存在")

        # 2. 查找或創建使用者影片互動記錄
        action = db.query(UserVideoAction).filter(
            UserVideoAction.user_no == current_user.user_no,
            UserVideoAction.video_no == video.video_no
        ).first()

        if action:
            # 切換收藏狀態
            action.is_favorite = 1 if action.is_favorite == 0 else 0
            message = "已加入收藏" if action.is_favorite == 1 else "已取消收藏"
        else:
            # 創建新記錄，預設為收藏
            action = UserVideoAction(
                user_no=current_user.user_no,
                video_no=video.video_no,
                is_favorite=1,
                is_watched=0
            )
            db.add(action)
            message = "已加入收藏"

        db.commit()
        db.refresh(action)

        logger.info(f"用戶 {current_user.user_no} {message}影片 {video_id}")

        return {
            "message": message,
            "video_id": video_id,
            "is_favorite": action.is_favorite
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"切換收藏失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/note/{video_id}")
async def save_video_note(
    video_id: str,
    request: NoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    儲存影片筆記

    - **video_id**: YouTube 影片 ID
    - **note**: 筆記內容

    Headers:
    - **Authorization**: Bearer {JWT_TOKEN}
    """
    note = request.note
    try:
        # 1. 查找影片
        video = db.query(YoutubeVideo).filter(
            YoutubeVideo.video_id == video_id
        ).first()

        if not video:
            raise HTTPException(status_code=404, detail="影片不存在")

        # 2. 查找或創建使用者影片互動記錄
        action = db.query(UserVideoAction).filter(
            UserVideoAction.user_no == current_user.user_no,
            UserVideoAction.video_no == video.video_no
        ).first()

        if action:
            # 更新筆記
            action.user_note = note
        else:
            # 創建新記錄
            action = UserVideoAction(
                user_no=current_user.user_no,
                video_no=video.video_no,
                is_favorite=0,
                is_watched=0,
                user_note=note
            )
            db.add(action)

        db.commit()
        db.refresh(action)

        logger.info(f"用戶 {current_user.user_no} 儲存影片 {video_id} 的筆記")

        return {
            "message": "筆記已儲存",
            "video_id": video_id,
            "user_note": action.user_note
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"儲存筆記失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
