"""
Briefing models
"""
from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey, Enum as SQLEnum, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base


class BriefingStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    DELIVERED = "delivered"
    FAILED = "failed"


class Briefing(Base):
    __tablename__ = "briefings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    status = Column(SQLEnum(BriefingStatus), default=BriefingStatus.PENDING, index=True)
    text_summary = Column(Text)
    audio_file_url = Column(String(1000))
    audio_duration_seconds = Column(Integer)
    content_items_count = Column(Integer, default=0)
    generated_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="briefings")
    briefing_content = relationship("BriefingContent", back_populates="briefing", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_briefing_user_date"),
    )


class BriefingContent(Base):
    __tablename__ = "briefing_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    briefing_id = Column(UUID(as_uuid=True), ForeignKey("briefings.id", ondelete="CASCADE"), nullable=False, index=True)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False)
    order = Column(Integer, nullable=False)
    included_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    briefing = relationship("Briefing", back_populates="briefing_content")
    content = relationship("ContentItem", back_populates="briefing_content")

    from sqlalchemy import Index
    __table_args__ = (
        UniqueConstraint("briefing_id", "content_id", name="uq_briefing_content"),
        Index("idx_briefing_order", "briefing_id", "order"),
    )

