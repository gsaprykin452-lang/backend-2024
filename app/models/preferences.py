"""
User preferences model
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from app.core.database import Base


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    categories_priority = Column(JSONB)
    topics_interest = Column(ARRAY(String))
    sources_priority = Column(JSONB)
    min_relevance_score = Column(Float, default=0.3)
    max_items_per_briefing = Column(Integer, default=10)
    language = Column(String(10), default="ru")
    voice_preference = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preferences")

