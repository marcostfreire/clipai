"""Celery tasks for asynchronous video processing."""

from celery import Celery
from sqlalchemy.orm import Session
import logging
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import SessionLocal
from app.models import Video, Clip
from app.services.ffmpeg_service import FFmpegService
from app.services.gemini_service import GeminiService
from app.services.whisper_service import WhisperService
from app.services.video_processor import VideoProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    "clipai", broker=settings.celery_broker_url, backend=settings.celery_result_backend
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_concurrency=settings.celery_worker_concurrency,
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
)


@celery_app.task(bind=True, name="process_video_task")
def process_video_task(
    self,
    video_id: str,
    clip_min_duration: int = None,
    clip_max_duration: int = None,
    min_virality_score: float = None,
) -> dict:
    """
    Process video and generate clips.

    Args:
        video_id: Video ID to process
        clip_min_duration: Minimum clip duration (uses settings default if None)
        clip_max_duration: Maximum clip duration (uses settings default if None)
        min_virality_score: Minimum virality score threshold (uses settings default if None)

    Returns:
        Dictionary with processing results
    """
    # Use provided values or fall back to settings defaults
    clip_min = clip_min_duration if clip_min_duration is not None else settings.clip_min_duration
    clip_max = clip_max_duration if clip_max_duration is not None else settings.clip_max_duration
    min_score = min_virality_score if min_virality_score is not None else settings.min_virality_score

    db: Session = SessionLocal()

    try:
        logger.info(f"[VIDEO:{video_id}] Task started")

        # Get video from database
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise ValueError(f"Video {video_id} not found")

        # Update status
        video.status = "processing"
        video.progress = 0
        db.commit()

        # Initialize services
        ffmpeg_service = FFmpegService(
            preset=settings.ffmpeg_preset,
            crf=settings.ffmpeg_crf,
            audio_bitrate=settings.ffmpeg_audio_bitrate,
        )
        ai_service = GeminiService(
            api_key=settings.google_api_key,
            model_default=settings.gemini_model_default,
            model_strict=settings.gemini_model_strict,
            batch_size=settings.ai_batch_size,
            timeout=settings.ai_timeout,
            max_retries=settings.ai_max_retries,
        )
        whisper_service = WhisperService(
            model_name=settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )

        # Initialize processor with custom or default parameters
        logger.info(f"[VIDEO:{video_id}] Using params: min_duration={clip_min}s, max_duration={clip_max}s, min_score={min_score}")
        processor = VideoProcessor(
            ffmpeg_service=ffmpeg_service,
            ai_service=ai_service,
            whisper_service=whisper_service,
            storage_path=settings.storage_path,
            frames_per_second=settings.frames_per_second,
            clip_min_duration=clip_min,
            clip_max_duration=clip_max,
            min_virality_score=min_score,
            subtitle_delay_seconds=settings.subtitle_delay_seconds,
        )

        # Progress callback
        def update_progress(progress: int, message: str):
            video.progress = progress
            db.commit()
            logger.info(f"[VIDEO:{video_id}] Progress: {progress}% - {message}")

            # Update Celery task state
            self.update_state(
                state="PROGRESS",
                meta={"progress": progress, "message": message, "video_id": video_id},
            )

        # Process video
        clips_metadata = processor.process_video(
            video_id=video_id,
            video_path=video.file_path,
            progress_callback=update_progress,
        )

        # Save clips to database
        for clip_meta in clips_metadata:
            clip = Clip(
                id=clip_meta["clip_id"],
                video_id=video_id,
                start_time=float(clip_meta["start_time"]),
                end_time=float(clip_meta["end_time"]),
                duration=float(clip_meta["duration"]),
                virality_score=float(clip_meta["virality_score"]),
                transcript=clip_meta["transcript"],
                keywords=clip_meta["keywords"],
                file_path=clip_meta["file_path"],
                thumbnail_path=clip_meta["thumbnail_path"],
                analysis_data=clip_meta["analysis_data"],
            )
            db.add(clip)

        # Update video status
        video.status = "completed"
        video.progress = 100
        db.commit()

        logger.info(f"[VIDEO:{video_id}] Processing completed successfully")

        return {
            "video_id": video_id,
            "status": "completed",
            "clips_count": len(clips_metadata),
        }

    except Exception as e:
        logger.error(f"[VIDEO:{video_id}] Processing failed: {e}", exc_info=True)

        # Update video with error
        if video:
            video.status = "failed"
            video.error_message = str(e)
            db.commit()

        raise

    finally:
        db.close()


@celery_app.task(name="cleanup_old_videos_task")
def cleanup_old_videos_task(days_old: int = 7) -> dict:
    """
    Clean up videos older than specified days.

    Args:
        days_old: Delete videos older than this many days

    Returns:
        Dictionary with cleanup results
    """
    db: Session = SessionLocal()

    try:
        from datetime import datetime, timedelta
        import shutil

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Find old videos
        old_videos = db.query(Video).filter(Video.created_at < cutoff_date).all()

        deleted_count = 0
        for video in old_videos:
            try:
                # Delete files
                video_dir = os.path.join(settings.storage_path, video.id)
                if os.path.exists(video_dir):
                    shutil.rmtree(video_dir)

                # Delete from database (cascade will delete clips)
                db.delete(video)
                deleted_count += 1

            except Exception as e:
                logger.error(f"Error deleting video {video.id}: {e}")

        db.commit()

        logger.info(f"Cleanup completed. Deleted {deleted_count} videos")

        return {"deleted_count": deleted_count, "cutoff_date": cutoff_date.isoformat()}

    except Exception as e:
        logger.error(f"Cleanup task failed: {e}", exc_info=True)
        raise

    finally:
        db.close()
