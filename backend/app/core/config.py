from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "VideoHub API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str
    DB_NAME: str = "db_youtubesubscribe"

    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Google Gemini API
    GOOGLE_API_KEY: str
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # YouTube API (僅用於新增頻道)
    YOUTUBE_API_KEY: Optional[str] = None

    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # JWT Authentication
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Scheduler
    WATCHER_INTERVAL_MINUTES: int = 15

    # Email / SMTP Settings
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: Optional[str] = None

    # LINE Messaging API Settings
    LINE_CHANNEL_SECRET: Optional[str] = None
    LINE_CHANNEL_ACCESS_TOKEN: Optional[str] = None
    LINE_BOT_BASE_URL: str = "http://localhost:8000"  # 從 .env 讀取
    FRONTEND_URL: str = "http://localhost:3000"  # 從 .env 讀取

    # Testing Mode (測試模式)
    TEST_MODE: bool = False  # 設為 True 時，會用 60 秒等待取代 Gemini API 呼叫

    # YouTube Cookies (Base64 編碼)
    YOUTUBE_COOKIES_BASE64: Optional[str] = None  # cookies.txt 的 base64 編碼內容

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False  # 改為 False，讓環境變數不區分大小寫
        extra = "ignore"


settings = Settings()
