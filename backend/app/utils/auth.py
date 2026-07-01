from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import get_db
from app.models.models import User
import logging

logger = logging.getLogger(__name__)

# HTTPBearer for JWT token
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    创建 JWT access token

    Args:
        data: 要编码的数据 (通常包含 user_id)
        expires_delta: 过期时间增量

    Returns:
        str: JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    验证 JWT token

    Args:
        token: JWT token 字符串

    Returns:
        dict: 解码后的payload

    Raises:
        HTTPException: token无效或过期
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = payload.get("user_id")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭证",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except JWTError as e:
        logger.error(f"Token验证失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    从 JWT token 中获取当前用户

    这是一个依赖注入函数，用于保护需要认证的API端点

    Args:
        credentials: HTTP Bearer token
        db: 数据库会话

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 认证失败
    """
    token = credentials.credentials
    payload = verify_token(token)
    user_id = payload.get("user_id")

    # 从数据库查询用户
    user = db.query(User).filter(User.user_no == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在"
        )

    if user.user_status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账号已被停用"
        )

    return user


async def get_current_active_premium_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    获取当前的 Premium 用户

    用于保护需要 Premium 会员权限的API端点

    Args:
        current_user: 当前用户

    Returns:
        User: Premium 用户对象

    Raises:
        HTTPException: 用户非Premium会员
    """
    if current_user.membership_level == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="此功能仅限 Premium 会员使用，请升级您的会员等级"
        )

    return current_user
