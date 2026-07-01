from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import YoutubeVideo, YoutubeChannel
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/video/{video_id}")
async def get_public_video_info(
    video_id: str,
    db: Session = Depends(get_db)
):
    """
    獲取影片基本資訊(公開 API,不需登入)

    用於公開播放頁面,只返回影片標題、頻道等基本資訊
    不返回摘要等需要登入才能查看的內容

    - **video_id**: YouTube 影片 ID
    """
    try:
        # 查詢影片和頻道資訊
        video = db.query(YoutubeVideo).filter(
            YoutubeVideo.video_id == video_id
        ).first()

        if not video:
            # 即使找不到影片,也返回基本結構(讓前端可以正常播放 YouTube embed)
            logger.warning(f"公開查詢:影片 {video_id} 不存在於資料庫")
            return {
                "video_id": video_id,
                "title": None,
                "channel_title": None,
                "thumbnail_url": None
            }

        # 查詢頻道資訊
        channel = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_no == video.channel_no
        ).first()

        return {
            "video_id": video.video_id,
            "title": video.title,
            "channel_title": channel.title if channel else None,
            "thumbnail_url": video.thumbnail_url
        }

    except Exception as e:
        logger.error(f"獲取公開影片資訊失敗: {str(e)}")
        # 即使發生錯誤,也返回基本結構
        return {
            "video_id": video_id,
            "title": None,
            "channel_title": None,
            "thumbnail_url": None
        }
