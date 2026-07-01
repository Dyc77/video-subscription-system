from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, UserSetting, AiTone, AiPersona
from app.models.schemas import UserSettingResponse, UserSettingUpdate
from app.utils.auth import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/user/setting", response_model=UserSettingResponse)
async def get_user_setting(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    獲取當前使用者的完整設定

    Headers:
    - **Authorization**: Bearer {JWT_TOKEN}

    Returns:
        UserSettingResponse: 包含通知設定與 AI 摘要設定
    """
    try:
        # 查詢使用者設定
        user_setting = db.query(UserSetting).filter(
            UserSetting.user_no == current_user.user_no
        ).first()

        if not user_setting:
            # 如果沒有設定記錄，創建預設值
            user_setting = UserSetting(
                user_no=current_user.user_no,
                notify_enable=1,
                notify_interval=30,
                enable_line=0,
                enable_email=1,
                ai_summary_length=300,
                ai_tone=AiTone.PROFESSIONAL.value,
                ai_persona=AiPersona.GENERAL.value
            )
            db.add(user_setting)
            db.commit()
            db.refresh(user_setting)
            logger.info(f"為用戶 {current_user.user_no} 創建預設設定")

        return user_setting

    except Exception as e:
        logger.error(f"獲取使用者設定失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/user/setting", response_model=UserSettingResponse)
async def update_user_setting(
    settings_update: UserSettingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新使用者設定（部分更新）

    Headers:
    - **Authorization**: Bearer {JWT_TOKEN}

    Body:
        UserSettingUpdate: 要更新的欄位（可選）

    Example:
    ```json
    {
        "notify_enable": 1,
        "notify_interval": 60,
        "enable_email": 1,
        "enable_line": 0,
        "ai_summary_length": 500,
        "ai_tone": "friendly",
        "ai_persona": "teacher"
    }
    ```
    """
    try:
        # 查詢使用者設定
        user_setting = db.query(UserSetting).filter(
            UserSetting.user_no == current_user.user_no
        ).first()

        if not user_setting:
            raise HTTPException(status_code=404, detail="使用者設定不存在，請重新登入")

        # 更新欄位（只更新有提供的欄位）
        update_data = settings_update.model_dump(exclude_unset=True)

        # 驗證 ai_tone 是否有效
        if 'ai_tone' in update_data:
            try:
                AiTone(update_data['ai_tone'])
            except ValueError:
                valid_tones = [tone.value for tone in AiTone]
                raise HTTPException(
                    status_code=400,
                    detail=f"無效的 ai_tone 值。有效值: {', '.join(valid_tones)}"
                )

        # 驗證 ai_persona 是否有效
        if 'ai_persona' in update_data:
            try:
                AiPersona(update_data['ai_persona'])
            except ValueError:
                valid_personas = [persona.value for persona in AiPersona]
                raise HTTPException(
                    status_code=400,
                    detail=f"無效的 ai_persona 值。有效值: {', '.join(valid_personas)}"
                )

        # 更新欄位
        for field, value in update_data.items():
            setattr(user_setting, field, value)

        db.commit()
        db.refresh(user_setting)

        logger.info(f"使用者 {current_user.user_no} 更新設定: {update_data}")

        return user_setting

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新使用者設定失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ai-options")
async def get_ai_options():
    """
    獲取 AI 摘要選項列表

    Returns:
        dict: 包含 tones 和 personas 的列表
    """
    return {
        "tones": [
            {"value": tone.value, "label": tone.name} for tone in AiTone
        ],
        "personas": [
            {"value": persona.value, "label": persona.name} for persona in AiPersona
        ],
        "summary_length_options": [100, 200, 300, 500, 800, 1000],
        "notify_interval_options": [30, 60, 120, 240, 360, 720, 1440]  # 分鐘
    }
