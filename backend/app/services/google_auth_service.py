from google.oauth2 import id_token
from google.auth.transport import requests
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class GoogleAuthService:
    """Google OAuth 认证服务"""

    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID

    def verify_google_token(self, token: str) -> dict:
        """
        验证 Google OAuth Token

        Args:
            token: Google ID Token (从前端 Google Sign-In 获取)

        Returns:
            dict: 用户信息
            {
                "google_uid": "...",
                "email": "...",
                "name": "...",
                "picture": "..."
            }

        Raises:
            ValueError: Token 无效
        """
        try:
            # 验证 Google ID Token
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                self.client_id
            )

            # 验证 issuer
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')

            # 提取用户信息
            user_info = {
                "google_uid": idinfo['sub'],  # Google User ID
                "email": idinfo.get('email'),
                "name": idinfo.get('name'),
                "picture": idinfo.get('picture'),
                "email_verified": idinfo.get('email_verified', False)
            }

            logger.info(f"Google 登录成功: {user_info['email']}")
            return user_info

        except ValueError as e:
            logger.error(f"Google Token 验证失败: {str(e)}")
            raise ValueError(f"无效的 Google Token: {str(e)}")

        except Exception as e:
            logger.error(f"Google 认证错误: {str(e)}")
            raise Exception(f"Google 认证失败: {str(e)}")


# 创建全局实例
google_auth_service = GoogleAuthService()
