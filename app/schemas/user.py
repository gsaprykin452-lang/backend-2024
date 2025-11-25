"""
User schemas
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import time
from app.models.user import SubscriptionStatus


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    timezone: Optional[str] = None
    briefing_time: Optional[time] = None


class UserPreferencesUpdate(BaseModel):
    categories_priority: Optional[dict] = None
    topics_interest: Optional[list[str]] = None
    sources_priority: Optional[dict] = None
    min_relevance_score: Optional[float] = None
    max_items_per_briefing: Optional[int] = None
    language: Optional[str] = None
    voice_preference: Optional[str] = None


class SubscriptionUpdate(BaseModel):
    subscription_status: SubscriptionStatus

