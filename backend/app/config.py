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

    # Ollama AI Service (local Gemma 3 4B)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma3:4b"

    # Storage
    storage_path: str = "./storage/videos"
    max_video_size_mb: int = 500
    max_video_duration_sec: int = 3600

    # Processing
    frames_per_second: float = (
        0.2  # Optimized: 1 frame every 5 seconds (was 0.33 = every 3s)
    )
    clip_min_duration: int = 30
    clip_max_duration: int = 60
    min_virality_score: float = 5.0  # Lowered to generate more clips
    subtitle_delay_seconds: float = 0.0  # Default to real-time captions

    # Performance optimization
    ai_batch_size: int = 5  # Number of frames to process in a single Ollama request

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = True

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
    stripe_price_free: Optional[str] = None  # price_xxx
    stripe_price_starter: Optional[str] = None  # price_xxx
    stripe_price_pro: Optional[str] = None  # price_xxx


settings = Settings()
