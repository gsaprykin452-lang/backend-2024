"""
User interaction model
"""
from sqlalchemy import Column, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base


class InteractionType(str, enum.Enum):
    PLAYED = "played"
    SKIPPED = "skipped"
    LIKED = "liked"
    DISLIKED = "disliked"
    SHARED = "shared"


class UserInteraction(Base):
    __tablename__ = "user_interactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    briefing_id = Column(UUID(as_uuid=True), ForeignKey("briefings.id", ondelete="SET NULL"))
    content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="SET NULL"))
    interaction_type = Column(SQLEnum(InteractionType), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="interactions")
    briefing = relationship("Briefing")
    content = relationship("ContentItem")

