"""
Data source schemas
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.data_source import SourceType


class DataSourceCreate(BaseModel):
    source_type: SourceType
    name: str
    settings: Optional[Dict[str, Any]] = None


class DataSourceResponse(BaseModel):
    id: str
    user_id: str
    source_type: SourceType
    name: str
    is_active: bool
    last_sync_at: Optional[datetime]
    sync_frequency_minutes: int
    settings: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TwitterOAuthInit(BaseModel):
    redirect_uri: str


class TwitterOAuthCallback(BaseModel):
    code: str
    state: str
    redirect_uri: str


class TelegramBotConnect(BaseModel):
    bot_token: str
    chat_ids: Optional[list[str]] = None  # Optional: specific chats to monitor


class FacebookOAuthInit(BaseModel):
    redirect_uri: str


class FacebookOAuthCallback(BaseModel):
    code: str
    state: str
    redirect_uri: str


class InstagramOAuthInit(BaseModel):
    redirect_uri: str


class InstagramOAuthCallback(BaseModel):
    code: str
    state: str
    redirect_uri: str
