"""
Content models
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Enum as SQLEnum, Float, ARRAY, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base


class ContentType(str, enum.Enum):
    POST = "post"
    ARTICLE = "article"
    MESSAGE = "message"
    NOTIFICATION = "notification"


class CategoryType(str, enum.Enum):
    PERSONAL = "personal"
    WORK = "work"
    HOBBY = "hobby"
    NEWS = "news"
    IMPORTANT = "important"
    OTHER = "other"


class ContentItem(Base):
    __tablename__ = "content_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    external_id = Column(String(255), nullable=False)
    content_type = Column(SQLEnum(ContentType), nullable=False)
    title = Column(String(500))
    text_content = Column(Text)
    url = Column(String(1000))
    author = Column(String(255))
    published_at = Column(DateTime(timezone=True), nullable=False, index=True)
    item_metadata = Column("metadata", JSONB)  # В БД колонка называется "metadata", в коде используем item_metadata
    raw_data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    source = relationship("DataSource", back_populates="content_items")
    classification = relationship("ContentClassification", back_populates="content", uselist=False, cascade="all, delete-orphan")
    briefing_content = relationship("BriefingContent", back_populates="content", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_content_source_external"),
    )


class ContentClassification(Base):
    __tablename__ = "content_classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_id = Column(UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False, unique=True)
    category = Column(SQLEnum(CategoryType), nullable=False, index=True)
    relevance_score = Column(Float, nullable=False)
    importance_score = Column(Float, nullable=False)
    social_score = Column(Float, nullable=False)
    personal_score = Column(Float, nullable=False)
    topics = Column(ARRAY(Text))
    classified_at = Column(DateTime(timezone=True), server_default=func.now())
    model_version = Column(String(50))

    # Relationships
    content = relationship("ContentItem", back_populates="classification")

    from sqlalchemy import Index
    __table_args__ = (
        Index("idx_relevance_importance", "relevance_score", "importance_score"),
    )

