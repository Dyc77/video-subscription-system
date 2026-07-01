from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import User, UserConfig, SystemParam, UserSetting
from app.models.schemas import Token, UserResponse
from app.utils.auth import create_access_token, get_current_user
from app.services.google_auth_service import google_auth_service
from passlib.context import CryptContext
from datetime import timedelta, datetime
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 密碼加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _ensure_user_setting(db: Session, user_no: int):
    """
    確保使用者有個人設定記錄 (新版 - 使用 tb_user_setting)
    如果不存在則自動建立（使用預設值）
    """
    try:
        # 檢查使用者是否已有設定
        existing_setting = db.query(UserSetting).filter(
            UserSetting.user_no == user_no
        ).first()

        if not existing_setting:
            # 建立預設設定
            new_setting = UserSetting(
                user_no=user_no,
                # 通知相關 - 使用資料表預設值
                notify_enable=1,  # 預設開啟
                notify_interval=30,  # 30分鐘
                enable_line=0,  # Line 預設關閉
                enable_email=1,  # Email 預設開啟
                # AI 摘要相關 - 使用資料表預設值
                ai_summary_length=300,
                ai_tone='professional',
                ai_persona='general'
            )
            db.add(new_setting)
            db.commit()
            logger.info(f"為使用者 {user_no} 建立預設設定（notify_enable=1, enable_email=1）")
    except Exception as e:
        logger.error(f"初始化使用者設定失敗: {str(e)}")
        db.rollback()
        # 不影響登入流程，繼續執行


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證密碼"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """密碼加密"""
    return pwd_context.hash(password)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    使用者登入，獲取 JWT token

    - **username**: 帳號/Email
    - **password**: 密碼

    Returns:
    - **access_token**: JWT token
    - **token_type**: Bearer
    """
    try:
        # 查詢使用者
        user = db.query(User).filter(User.account == form_data.username).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="帳號或密碼錯誤",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 驗證密碼
        if not verify_password(form_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="帳號或密碼錯誤",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 檢查使用者狀態
        if user.user_status != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="帳號已被停用"
            )

        # 生成 JWT token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"user_id": user.user_no},
            expires_delta=access_token_expires
        )

        # 更新最後登入時間
        user.last_login_time = datetime.utcnow()
        db.commit()

        # 確保使用者有個人設定記錄（新版 - 使用 tb_user_setting）
        _ensure_user_setting(db, user.user_no)

        logger.info(f"使用者 {user.account} 登入成功")

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"登入失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登入失敗: {str(e)}"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    獲取當前登入使用者資訊

    Headers:
    - **Authorization**: Bearer {JWT_TOKEN}
    """
    return current_user


@router.post("/google-login", response_model=Token)
async def google_login(
    google_token: str = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Google 登入

    驗證 Google ID Token 並自動建立/登入使用者

    **請求體**:
    ```json
    {
      "google_token": "Google ID Token from frontend"
    }
    ```

    **流程**:
    1. 驗證 Google ID Token
    2. 檢查使用者是否存在 (透過 google_uid)
    3. 不存在則自動建立新使用者
    4. 返回 JWT Token

    Returns:
    - **access_token**: JWT token
    - **token_type**: Bearer
    """
    try:
        # 1. 驗證 Google Token
        google_user_info = google_auth_service.verify_google_token(google_token)

        if not google_user_info.get('email_verified'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google 帳號信箱未驗證"
            )

        google_uid = google_user_info['google_uid']
        email = google_user_info['email']

        # 2. 查詢使用者是否已存在
        user = db.query(User).filter(User.google_uid == google_uid).first()

        if not user:
            # 2.1 使用者不存在，檢查信箱是否已被使用
            existing_user = db.query(User).filter(User.account == email).first()

            if existing_user:
                # 信箱已存在但沒有關聯 Google UID，進行關聯
                existing_user.google_uid = google_uid
                if not existing_user.email:  # 補充 email 欄位（針對舊使用者）
                    existing_user.email = email
                user = existing_user
                logger.info(f"關聯 Google 帳號: {email}")
            else:
                # 2.2 建立新使用者
                user = User(
                    account=email,
                    email=email,  # 第一次登入回寫 email
                    google_uid=google_uid,
                    password=None,  # Google 登入無需密碼
                    user_status=1,
                    membership_level=0,  # 預設免費會員
                    last_login_time=datetime.utcnow()
                )
                db.add(user)
                logger.info(f"建立新 Google 使用者: {email}")

        # 3. 檢查使用者狀態
        if user.user_status != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="帳號已被停用"
            )

        # 4. 更新最後登入時間
        user.last_login_time = datetime.utcnow()
        db.commit()
        db.refresh(user)

        # 5. 確保使用者有個人設定記錄（新版 - 使用 tb_user_setting）
        _ensure_user_setting(db, user.user_no)

        # 6. 生成 JWT Token（包含使用者資訊）
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "user_id": user.user_no,
                "email": user.email or user.account,
                "picture": google_user_info.get('picture')  # Google 頭像
            },
            expires_delta=access_token_expires
        )

        logger.info(f"Google 使用者 {email} 登入成功")

        return {
            "access_token": access_token,
            "token_type": "bearer"
        }

    except ValueError as e:
        # Google Token 驗證失敗
        logger.error(f"Google Token 驗證失敗: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Google 登入失敗: {str(e)}"
        )

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        logger.error(f"Google 登入錯誤: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登入失敗: {str(e)}"
        )
