from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, UserSubscription, YoutubeChannel
from app.models.schemas import UserResponse, SubscriptionCreate, SubscriptionResponse
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    獲取使用者資訊

    - **user_id**: 使用者 ID
    """
    try:
        user = db.query(User).filter(User.user_no == user_id).first()

        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"獲取使用者資訊失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{user_id}/subscribe", response_model=SubscriptionResponse)
async def subscribe_channel(
    user_id: int,
    request: SubscriptionCreate,
    db: Session = Depends(get_db)
):
    """
    訂閱頻道

    - **user_id**: 使用者 ID
    - **channel_id**: YouTube 頻道 ID
    """
    try:
        # 檢查使用者是否存在
        user = db.query(User).filter(User.user_no == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="使用者不存在")

        # 檢查頻道是否存在
        channel = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_id == request.channel_id
        ).first()

        if not channel:
            raise HTTPException(status_code=404, detail="頻道不存在")

        # 檢查是否已訂閱
        existing_sub = db.query(UserSubscription).filter(
            UserSubscription.user_no == user_id,
            UserSubscription.channel_no == channel.channel_no
        ).first()

        if existing_sub:
            raise HTTPException(status_code=400, detail="已訂閱該頻道")

        # 建立訂閱
        subscription = UserSubscription(
            user_no=user_id,
            channel_no=channel.channel_no
        )

        db.add(subscription)
        db.commit()
        db.refresh(subscription)

        return subscription

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"訂閱頻道失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}/subscribe/{channel_id}")
async def unsubscribe_channel(
    user_id: int,
    channel_id: str,
    db: Session = Depends(get_db)
):
    """
    取消訂閱頻道

    - **user_id**: 使用者 ID
    - **channel_id**: YouTube 頻道 ID
    """
    try:
        # 查找頻道
        channel = db.query(YoutubeChannel).filter(
            YoutubeChannel.channel_id == channel_id
        ).first()

        if not channel:
            raise HTTPException(status_code=404, detail="頻道不存在")

        # 查找訂閱記錄
        subscription = db.query(UserSubscription).filter(
            UserSubscription.user_no == user_id,
            UserSubscription.channel_no == channel.channel_no
        ).first()

        if not subscription:
            raise HTTPException(status_code=404, detail="未訂閱該頻道")

        # 刪除訂閱
        db.delete(subscription)
        db.commit()

        return {"message": "取消訂閱成功"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"取消訂閱失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/subscriptions", response_model=List[SubscriptionResponse])
async def get_user_subscriptions(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    獲取使用者的訂閱列表

    - **user_id**: 使用者 ID
    """
    try:
        subscriptions = db.query(UserSubscription).filter(
            UserSubscription.user_no == user_id
        ).order_by(UserSubscription.subscribed_at.desc()).all()

        return subscriptions

    except Exception as e:
        logger.error(f"獲取訂閱列表失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
