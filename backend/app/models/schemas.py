from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    account: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    user_no: int
    user_status: int
    membership_level: int
    create_time: datetime

    class Config:
        from_attributes = True


# Channel Schemas
class ChannelBase(BaseModel):
    channel_id: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None


class ChannelCreateByUrl(BaseModel):
    """使用 YouTube 頻道網址新增頻道"""
    channel_url: str


class ChannelCreate(ChannelBase):
    rss_url: str


class ChannelResponse(ChannelBase):
    channel_no: int
    channel_status: int
    create_time: datetime

    class Config:
        from_attributes = True


# Video Schemas
class VideoBase(BaseModel):
    video_id: str
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    video_url: Optional[str] = None
    published_at: Optional[datetime] = None


class VideoResponse(VideoBase):
    video_no: int
    channel_no: int
    summary_status: int
    summary_content: Optional[str] = None
    create_time: datetime
    is_favorite: Optional[int] = 0  # 收藏狀態: 0-未收藏, 1-已收藏
    user_note: Optional[str] = None  # 使用者筆記

    class Config:
        from_attributes = True


# Summary Schemas
class SummaryRequest(BaseModel):
    video_id: str
    # user_id 从 JWT token 中解析，安全性考虑不从前端传入


class SummaryResponse(BaseModel):
    video_id: str
    summary_status: int
    summary_content: Optional[str] = None
    message: Optional[str] = None
    estimated_wait_seconds: Optional[int] = None  # 预估等待时间（秒）


# Note Schemas
class NoteRequest(BaseModel):
    note: str


# Subscription Schemas
class SubscriptionCreate(BaseModel):
    channel_id: str


class SubscriptionResponse(BaseModel):
    subscription_no: int
    user_no: int
    channel_no: int
    is_notification_enabled: int
    create_time: datetime

    class Config:
        from_attributes = True


# Auth Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None


# User Setting Schemas (新設計 - 取代 SystemParam + UserConfig)
class UserSettingResponse(BaseModel):
    """使用者設定回應 (完整設定)"""
    user_no: int
    # 通知相關
    notify_enable: int  # 0:全關, 1:全開
    notify_interval: int  # 通知間隔（分鐘）
    enable_line: int  # 0:關, 1:開
    enable_email: int  # 0:關, 1:開
    # AI 摘要相關
    ai_summary_length: int  # 期望字數
    ai_tone: str  # professional, humorous, friendly, concise, critical, encouraging
    ai_persona: str  # general, engineer, teacher, investor, critic, summarizer
    # 系統欄位
    updated_at: datetime

    class Config:
        from_attributes = True


class UserSettingUpdate(BaseModel):
    """使用者設定更新 (部分更新)"""
    # 通知相關（可選）
    notify_enable: Optional[int] = None
    notify_interval: Optional[int] = None
    enable_line: Optional[int] = None
    enable_email: Optional[int] = None
    # AI 摘要相關（可選）
    ai_summary_length: Optional[int] = None
    ai_tone: Optional[str] = None
    ai_persona: Optional[str] = None


# ========== 保留舊的 Schemas (暫時相容) ==========
class SystemParamResponse(BaseModel):
    """系統參數回應 (舊版 - 準備廢棄)"""
    param_no: int
    sort: int
    caption: str
    value: str

    class Config:
        from_attributes = True


class UserConfigResponse(BaseModel):
    """使用者設定回應 (舊版 - 準備廢棄)"""
    param_no: int
    caption: str
    value: int  # 0:關閉, 1:開啟

    class Config:
        from_attributes = True


class UserConfigUpdate(BaseModel):
    """使用者設定更新 (舊版 - 準備廢棄)"""
    param_value: str  # "email", "line" 等
    enabled: bool  # True:開啟, False:關閉
