"""
User model
"""
from sqlalchemy import Column, String, Boolean, Time, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
import enum
from app.core.database import Base


class SubscriptionStatus(str, enum.Enum):
    FREE = "free"
    TRIAL = "trial"
    ACTIVE = "active"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    timezone = Column(String(50), default="UTC")
    briefing_time = Column(Time, default="08:00")
    is_active = Column(Boolean, default=True)
    subscription_status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.FREE)
    subscription_expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    data_sources = relationship("DataSource", back_populates="user", cascade="all, delete-orphan")
    briefings = relationship("Briefing", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    interactions = relationship("UserInteraction", back_populates="user", cascade="all, delete-orphan")

