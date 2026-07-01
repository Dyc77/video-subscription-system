"""
LINE 綁定碼暫存模型
使用記憶體字典儲存，簡單快速
"""
from datetime import datetime, timedelta
import random
import string

class LineBindingCodeStore:
    """LINE 綁定碼儲存"""

    def __init__(self):
        # 格式: {binding_code: {"user_id": int, "expires_at": datetime}}
        self.codes = {}

    def generate_code(self, user_id: int) -> str:
        """
        為使用者生成綁定碼

        Args:
            user_id: 使用者 ID

        Returns:
            str: 6位數綁定碼
        """
        # 移除該使用者之前的綁定碼
        self.codes = {k: v for k, v in self.codes.items() if v["user_id"] != user_id}

        # 生成新的 6 位數綁定碼
        while True:
            code = ''.join(random.choices(string.digits, k=6))
            if code not in self.codes:
                break

        # 儲存綁定碼，10分鐘有效
        self.codes[code] = {
            "user_id": user_id,
            "expires_at": datetime.utcnow() + timedelta(minutes=10)
        }

        return code

    def verify_code(self, code: str) -> int | None:
        """
        驗證綁定碼並返回使用者 ID

        Args:
            code: 綁定碼

        Returns:
            int | None: 使用者 ID，如果無效則返回 None
        """
        if code not in self.codes:
            return None

        data = self.codes[code]

        # 檢查是否過期
        if datetime.utcnow() > data["expires_at"]:
            del self.codes[code]
            return None

        return data["user_id"]

    def consume_code(self, code: str) -> int | None:
        """
        使用綁定碼（一次性）

        Args:
            code: 綁定碼

        Returns:
            int | None: 使用者 ID，如果無效則返回 None
        """
        user_id = self.verify_code(code)
        if user_id:
            del self.codes[code]
        return user_id

    def cleanup_expired(self):
        """清理過期的綁定碼"""
        now = datetime.utcnow()
        self.codes = {k: v for k, v in self.codes.items() if v["expires_at"] > now}


# 全局實例
binding_code_store = LineBindingCodeStore()
