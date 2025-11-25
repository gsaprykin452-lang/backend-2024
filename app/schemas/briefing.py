"""
Briefing schemas
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from app.models.briefing import BriefingStatus


class BriefingResponse(BaseModel):
    id: str
    user_id: str
    date: date
    status: BriefingStatus
    text_summary: Optional[str]
    audio_file_url: Optional[str]
    audio_duration_seconds: Optional[int]
    content_items_count: int
    generated_at: Optional[datetime]
    delivered_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class BriefingContentResponse(BaseModel):
    id: str
    content_id: str
    order: int
    included_reason: Optional[str]
    content_title: Optional[str]
    content_text: Optional[str]

    class Config:
        from_attributes = True


class BriefingDetailResponse(BriefingResponse):
    content_items: List[BriefingContentResponse] = []

