"""SQLAlchemy database models."""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base
import uuid


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)  # Nullable for OAuth users
    oauth_provider = Column(String, nullable=True)  # google, github, etc
    oauth_id = Column(String, nullable=True)  # Provider's user ID
    full_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    subscription_tier = Column(String, default="free")  # free, starter, pro
    subscription_status = Column(String, default="active")  # active, cancelled, expired
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (Index("ix_users_email", "email"),)


class Video(Base):
    """Video model representing uploaded videos."""

    __tablename__ = "videos"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    duration = Column(Float, nullable=True)  # seconds
    status = Column(String, default="queued")  # queued, processing, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(
        DateTime(timezone=True), onupdate=func.now(), server_default=func.now()
    )

    # Relationships
    clips = relationship("Clip", back_populates="video", cascade="all, delete-orphan")
    user = relationship("User", backref="videos")


class Clip(Base):
    """Clip model representing generated video clips."""

    __tablename__ = "clips"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id = Column(
        String, ForeignKey("videos.id", ondelete="CASCADE"), nullable=False
    )
    start_time = Column(Float, nullable=False)  # seconds
    end_time = Column(Float, nullable=False)  # seconds
    duration = Column(Float, nullable=False)  # seconds
    virality_score = Column(Float, nullable=False)  # 0-10
    transcript = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # array of strings
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String, nullable=True)
    analysis_data = Column(JSON, nullable=True)  # raw analysis data
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    video = relationship("Video", back_populates="clips")
