"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


# =====================
# Authentication Schemas
# =====================


class UserCreate(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class UserRead(BaseModel):
    """Response schema for user data."""

    id: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Response schema for token."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""

    email: Optional[str] = None


# =====================
# Video & Clip Schemas
# =====================


class VideoUploadResponse(BaseModel):
    """Response schema for video upload."""

    video_id: str
    status: str
    message: str


class VideoProcessRequest(BaseModel):
    """Request schema for video processing."""

    clip_duration_min: Optional[int] = Field(default=None, ge=10, le=60)
    clip_duration_max: Optional[int] = Field(default=None, ge=30, le=120)
    min_score: Optional[float] = Field(default=None, ge=0, le=10)


class VideoProcessResponse(BaseModel):
    """Response schema for process initiation."""

    job_id: str
    video_id: str
    status: str


class VideoStatusResponse(BaseModel):
    """Response schema for video status."""

    video_id: str
    status: str
    progress: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ClipResponse(BaseModel):
    """Response schema for individual clip."""

    clip_id: str
    start_time: float
    end_time: float
    duration: float
    virality_score: float
    transcript: Optional[str] = None
    keywords: Optional[List[str]] = None
    thumbnail_url: str
    download_url: str
    created_at: datetime

    class Config:
        from_attributes = True


class ClipsListResponse(BaseModel):
    """Response schema for list of clips."""

    video_id: str
    clips: List[ClipResponse]
    total: int


class ErrorResponse(BaseModel):
    """Response schema for errors."""

    error: str
    detail: Optional[str] = None
