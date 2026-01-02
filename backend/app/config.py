"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )

    # Database
    database_url: str = "postgresql://postgres:password@localhost:5432/clipai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Gemini AI Service
    google_api_key: Optional[str] = None
    gemini_model_default: str = "gemini-2.5-flash-lite"
    gemini_model_strict: str = "gemini-2.5-flash"

    # Storage (use /data/videos on Railway for persistent disk)
    storage_path: str = "./storage/videos"
    max_video_size_mb: int = 2048  # 2GB - realistic for modern video quality
    max_video_duration_sec: int = 7200  # 2 hours

    # Processing - optimized for Railway Hobby plan
    frames_per_second: float = 0.1  # 1 frame every 10 seconds (optimized for cost/performance)
    clip_min_duration: int = 30
    clip_max_duration: int = 60
    min_virality_score: float = 3.0  # Lowered from 5.0 to avoid rejecting good clips
    subtitle_delay_seconds: float = 0.0

    # Performance optimization
    ai_batch_size: int = 2  # Number of frames to process per batch (reduced for memory)
    ai_timeout: int = 120  # Gemini API timeout in seconds
    ai_max_retries: int = 3  # Max retries for API calls

    # Whisper settings
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # FFmpeg optimization
    ffmpeg_preset: str = "ultrafast"
    ffmpeg_crf: int = 26
    ffmpeg_audio_bitrate: str = "96k"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"
    celery_worker_concurrency: int = 1
    celery_worker_prefetch_multiplier: int = 1

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # JWT Authentication
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expires_minutes: int = 30

    # OAuth Providers
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    oauth_redirect_uri: str = "http://localhost:8000/api/auth/callback"

    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    stripe_price_free: Optional[str] = None
    stripe_price_starter: Optional[str] = None
    stripe_price_pro: Optional[str] = None

    # Cloudflare R2 Storage
    r2_account_id: Optional[str] = None
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_bucket_name: Optional[str] = None
    r2_public_url: Optional[str] = None  # e.g., https://storage.yourdomain.com

    # CORS
    cors_origins: str = "*"

    # Cleanup
    cleanup_days_old: int = 7


settings = Settings()
