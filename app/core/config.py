"""
Application configuration
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Daily Digest"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",  # Web версия Daily Digest
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ]
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/daily_digest"
    DATABASE_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    
    # ElevenLabs TTS
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Default voice
    
    # Twitter OAuth
    TWITTER_CLIENT_ID: str = ""
    TWITTER_CLIENT_SECRET: str = ""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    
    # Facebook OAuth
    FACEBOOK_APP_ID: str = ""
    FACEBOOK_APP_SECRET: str = ""
    
    # Instagram OAuth
    INSTAGRAM_APP_ID: str = ""
    INSTAGRAM_APP_SECRET: str = ""
    
    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    
    # Briefing settings
    BRIEFING_DURATION_SECONDS: int = 120  # 2 minutes
    BRIEFING_GENERATION_START_MINUTES: int = 10  # За 10 минут до времени брифинга
    
    # Content processing
    CONTENT_SYNC_INTERVAL_MINUTES: int = 15
    MAX_CONTENT_ITEMS_PER_BRIEFING: int = 10
    MIN_RELEVANCE_SCORE: float = 0.3
    
    # Storage (S3/Azure Blob)
    STORAGE_TYPE: str = "local"  # local, s3, azure
    STORAGE_BUCKET: str = "daily-digest-audio"
    STORAGE_LOCAL_PATH: str = "./storage"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

