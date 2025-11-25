"""
Data source model
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base


class SourceType(str, enum.Enum):
    TWITTER = "twitter"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TELEGRAM = "telegram"
    RSS = "rss"
    EMAIL = "email"


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(SQLEnum(SourceType), nullable=False)
    name = Column(String(255), nullable=False)
    credentials = Column(JSONB)  # Зашифрованные OAuth токены
    is_active = Column(Boolean, default=True)
    last_sync_at = Column(DateTime(timezone=True))
    sync_frequency_minutes = Column(Integer, default=15)
    settings = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="data_sources")
    content_items = relationship("ContentItem", back_populates="source", cascade="all, delete-orphan")
    sync_logs = relationship("SyncLog", back_populates="source", cascade="all, delete-orphan")

