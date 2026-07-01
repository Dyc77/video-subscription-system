from sqlalchemy import Column, Integer, String, Text, DateTime, SmallInteger, ForeignKey, Index, DECIMAL
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base
from enum import Enum


class AiTone(Enum):
    """
    摘要的語氣風格
    """
    PROFESSIONAL = "professional"  # 專業、正式 (適合新聞、財經)
    HUMOROUS = "humorous"          # 幽默、風趣 (適合生活、娛樂)
    FRIENDLY = "friendly"          # 親切、口語 (適合 Vlog、教學)
    CONCISE = "concise"            # 簡潔、直白 (適合快速獲取資訊)
    CRITICAL = "critical"          # 批判、犀利 (適合評論類)
    ENCOURAGING = "encouraging"    # 鼓勵、雞湯 (適合成長類)


class AiPersona(Enum):
    """
    AI 扮演的角色 (決定切入觀點)
    """
    GENERAL = "general"            # 一般助理 (預設值)
    ENGINEER = "engineer"          # 工程師 (關注技術細節、邏輯、架構)
    TEACHER = "teacher"            # 老師 (關注如何解釋、重點整理、適合初學者)
    INVESTOR = "investor"          # 投資者 (關注商業價值、成本效益、風險)
    CRITIC = "critic"              # 影評/樂評人 (關注藝術性、優缺點)
    SUMMARIZER = "summarizer"      # 專業摘要員 (只關注重點，不帶個人情緒)


class User(Base):
    """用户表"""
    __tablename__ = "tb_user"

    user_no = Column(Integer, primary_key=True, autoincrement=True, comment="使用者編號")
    account = Column(String(100), nullable=False, unique=True, index=True, comment="帳號/Email")
    email = Column(String(255), comment="使用者 Email (從 Google OAuth 取得)")
    password = Column(String(255), comment="密碼 (Google登入可為空)")
    google_uid = Column(String(255), unique=True, comment="Google UID")
    user_status = Column(SmallInteger, default=1, comment="1:啟用 0:停用")
    membership_level = Column(SmallInteger, default=0, comment="0:免費會員, 1:付費會員(Premium)")
    line_user_id = Column(String(255), comment="LINE Notify Token")
    last_login_time = Column(DateTime)
    create_time = Column(DateTime, default=datetime.utcnow)
    modify_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    subscriptions = relationship("UserSubscription", back_populates="user")


class YoutubeChannel(Base):
    """YouTube频道表 - 全域共用"""
    __tablename__ = "tb_youtubechannel"

    channel_no = Column(Integer, primary_key=True, autoincrement=True)
    channel_id = Column(String(100), nullable=False, unique=True, index=True, comment="YouTube官方頻道ID")
    title = Column(String(255), comment="頻道名稱")
    thumbnail_url = Column(String(500), comment="頻道頭像")
    rss_url = Column(String(255), comment="RSS監測網址 (系統生成)")
    uploads_playlist_id = Column(String(100), comment="上傳播放清單ID (省Quota備用)")
    last_check_time = Column(DateTime, comment="系統上次爬蟲時間")
    channel_status = Column(SmallInteger, default=1, comment="1:正常監測 0:停止監測")
    create_time = Column(DateTime, default=datetime.utcnow)

    # 关系
    videos = relationship("YoutubeVideo", back_populates="channel")
    subscriptions = relationship("UserSubscription", back_populates="channel")


class YoutubeVideo(Base):
    """YouTube影片表 - 全域共用"""
    __tablename__ = "tb_youtubevideo"

    video_no = Column(Integer, primary_key=True, autoincrement=True)
    channel_no = Column(Integer, ForeignKey("tb_youtubechannel.channel_no", ondelete="CASCADE"), nullable=False, comment="FK:所屬頻道")
    video_id = Column(String(100), nullable=False, unique=True, index=True, comment="YouTube影片ID")
    title = Column(String(500), comment="影片標題")
    video_url = Column(String(500), comment="影片連結")
    thumbnail_url = Column(String(500), comment="影片縮圖")
    published_at = Column(DateTime, comment="影片發布時間")
    transcript_text = Column(Text, comment="原始字幕 (除錯與重新生成用)")
    summary_content = Column(Text, comment="Gemini 生成的 Markdown 摘要 (全域共用)")
    summary_status = Column(SmallInteger, default=0, comment="0:未處理, 1:處理中, 2:完成, 3:失敗/無字幕")
    create_time = Column(DateTime, default=datetime.utcnow)

    # 关系
    channel = relationship("YoutubeChannel", back_populates="videos")

    # 索引
    __table_args__ = (
        Index('fk_video_channel', 'channel_no'),
    )


class UserSubscription(Base):
    """用户订阅表 - 多对多关系"""
    __tablename__ = "tb_usersubscription"

    subscription_no = Column(Integer, primary_key=True, autoincrement=True)
    user_no = Column(Integer, ForeignKey("tb_user.user_no", ondelete="CASCADE"), nullable=False, comment="FK:使用者")
    channel_no = Column(Integer, ForeignKey("tb_youtubechannel.channel_no", ondelete="CASCADE"), nullable=False, comment="FK:頻道")
    is_notification_enabled = Column(SmallInteger, default=1, comment="是否接收此頻道的通知")
    create_time = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="subscriptions")
    channel = relationship("YoutubeChannel", back_populates="subscriptions")

    # 唯一约束和索引
    __table_args__ = (
        Index('uk_user_channel', 'user_no', 'channel_no', unique=True),
        Index('fk_sub_channel', 'channel_no'),
    )


class UserVideoAction(Base):
    """使用者影片互動表"""
    __tablename__ = "tb_uservideoaction"

    action_no = Column(Integer, primary_key=True, autoincrement=True)
    user_no = Column(Integer, ForeignKey("tb_user.user_no", ondelete="CASCADE"), nullable=False)
    video_no = Column(Integer, ForeignKey("tb_youtubevideo.video_no", ondelete="CASCADE"), nullable=False)
    is_favorite = Column(SmallInteger, default=0, comment="是否收藏")
    is_watched = Column(SmallInteger, default=0, comment="是否已讀/已看")
    user_note = Column(Text, comment="使用者私人筆記 (私有資料)")
    last_click_time = Column(DateTime)
    create_time = Column(DateTime, default=datetime.utcnow)

    # 唯一约束和索引
    __table_args__ = (
        Index('uk_user_video', 'user_no', 'video_no', unique=True),
        Index('fk_action_video', 'video_no'),
    )


class SystemParam(Base):
    """系統參數總表 - 通知方式等系統級設定"""
    __tablename__ = "tb_systemparam"

    param_no = Column(Integer, primary_key=True, autoincrement=True, comment="參數編號")
    sort = Column(Integer, nullable=False, comment="排序")
    caption = Column(String(100), nullable=False, comment="參數名稱 (顯示用)")
    value = Column(String(100), nullable=False, unique=True, comment="參數值 (程式用)")
    create_time = Column(DateTime, default=datetime.utcnow)


class UserConfig(Base):
    """使用者設定表 - 每個使用者的個人化設定"""
    __tablename__ = "tb_config"

    config_no = Column(Integer, primary_key=True, autoincrement=True, comment="設定編號")
    user_no = Column(Integer, ForeignKey("tb_user.user_no", ondelete="CASCADE"), nullable=False, comment="FK:使用者")
    param_no = Column(Integer, ForeignKey("tb_systemparam.param_no", ondelete="CASCADE"), nullable=False, comment="FK:參數")
    config_value = Column(String(500), comment="設定值")
    modify_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 唯一约束和索引
    __table_args__ = (
        Index('uk_user_param', 'user_no', 'param_no', unique=True),
    )


class NotificationLog(Base):
    """通知發送紀錄表 - 防止重複發送通知"""
    __tablename__ = "tb_notificationlog"

    log_id = Column(Integer, primary_key=True, autoincrement=True, comment="紀錄編號")
    user_no = Column(Integer, ForeignKey("tb_user.user_no", ondelete="CASCADE"), nullable=False, comment="FK:使用者")
    video_no = Column(Integer, ForeignKey("tb_youtubevideo.video_no", ondelete="CASCADE"), nullable=False, comment="FK:影片")
    channel_no = Column(Integer, ForeignKey("tb_youtubechannel.channel_no", ondelete="CASCADE"), nullable=False, comment="FK:頻道")
    send_method = Column(String(20), default='email', comment="發送方式 (email/line)")
    send_time = Column(DateTime, default=datetime.utcnow, comment="發送時間")
    is_success = Column(SmallInteger, default=1, comment="發送成功 (1:成功, 0:失敗)")

    # 索引
    __table_args__ = (
        Index('idx_user_video', 'user_no', 'video_no'),
        Index('idx_send_time', 'send_time'),
    )


class UserSetting(Base):
    """使用者全域設定表 (通知與AI偏好) - 取代 tb_systemparam + tb_config"""
    __tablename__ = "tb_user_setting"

    # 主鍵：直接使用 user_no，與 tb_user 一對一
    user_no = Column(Integer, ForeignKey("tb_user.user_no", ondelete="CASCADE"), primary_key=True, comment="使用者編號")

    # 【通知相關設定】
    notify_enable = Column(SmallInteger, nullable=False, default=1, comment="通知總開關 (0:全關, 1:全開) - 勿擾模式用")
    notify_interval = Column(Integer, nullable=False, default=30, comment="通知最小間隔 (分鐘)")
    enable_line = Column(SmallInteger, nullable=False, default=0, comment="Line 通知開關 (0:關, 1:開)")
    enable_email = Column(SmallInteger, nullable=False, default=1, comment="Email 通知開關 (0:關, 1:開)")

    # 【AI 摘要相關設定】
    ai_summary_length = Column(Integer, nullable=False, default=300, comment="期望摘要字數 (例如 300, 500)")
    ai_tone = Column(String(30), nullable=False, default=AiTone.PROFESSIONAL.value, comment="摘要語氣 (對應 AiTone Enum)")
    ai_persona = Column(String(30), nullable=False, default=AiPersona.GENERAL.value, comment="摘要角色設定 (對應 AiPersona Enum)")

    # 【系統欄位】
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="最後修改時間")
