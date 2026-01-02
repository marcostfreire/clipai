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
from app.services.storage_service import get_storage_service

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

        # Initialize storage service
        storage = get_storage_service()

        # Download video from R2 if needed
        video_path = video.file_path
        local_video_path = storage.get_local_path(video_id, "original.mp4")
        
        # Check if we need to download from R2
        needs_download = False
        
        if storage.use_r2:
            if video_path.startswith("r2://") or (storage.r2_public_url and video_path.startswith(storage.r2_public_url)):
                # Path is explicitly R2
                needs_download = True
            elif not os.path.exists(video_path):
                # Local path doesn't exist - try to download from R2
                logger.info(f"[VIDEO:{video_id}] Local file not found at {video_path}, checking R2...")
                needs_download = True
                # Construct R2 key from video_id
                video_path = f"r2://{storage.r2_bucket_name}/{video_id}/original.mp4"
        
        if needs_download and storage.use_r2:
            logger.info(f"[VIDEO:{video_id}] Downloading from R2 to {local_video_path}")
            try:
                storage.download_file(video_path, local_video_path)
                video_path = local_video_path
                logger.info(f"[VIDEO:{video_id}] Download completed")
            except Exception as e:
                logger.error(f"[VIDEO:{video_id}] Failed to download from R2: {e}")
                raise ValueError(f"Video file not found locally or in R2: {video_path}")
        else:
            # Local file - verify it exists
            if not os.path.exists(video_path):
                raise ValueError(f"Video file not found: {video_path}")
            local_video_path = video_path

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
            video_path=local_video_path,
            progress_callback=update_progress,
        )

        # Upload clips to R2 if configured
        if storage.use_r2:
            logger.info(f"[VIDEO:{video_id}] Uploading clips to R2")
            for clip_meta in clips_metadata:
                # Upload video
                if os.path.exists(clip_meta["file_path"]):
                    r2_video_path = storage.upload_file(
                        clip_meta["file_path"],
                        video_id,
                        os.path.basename(clip_meta["file_path"])
                    )
                    clip_meta["file_path"] = r2_video_path

                # Upload thumbnail
                if os.path.exists(clip_meta["thumbnail_path"]):
                    r2_thumb_path = storage.upload_file(
                        clip_meta["thumbnail_path"],
                        video_id,
                        os.path.basename(clip_meta["thumbnail_path"])
                    )
                    clip_meta["thumbnail_path"] = r2_thumb_path

            # Upload original video too
            if os.path.exists(local_video_path):
                r2_original_path = storage.upload_file(
                    local_video_path,
                    video_id,
                    "original.mp4"
                )
                video.file_path = r2_original_path
                logger.info(f"[VIDEO:{video_id}] Original video uploaded to R2")

            # Clean up local temp files
            import shutil
            local_video_dir = storage.get_local_path(video_id)
            if os.path.exists(local_video_dir):
                shutil.rmtree(local_video_dir)
                logger.info(f"[VIDEO:{video_id}] Cleaned up local temp files")

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


@celery_app.task(name="detect_stuck_videos_task")
def detect_stuck_videos_task(stuck_threshold_minutes: int = 60) -> dict:
    """
    Detect and reset videos stuck in 'processing' status.
    
    This task identifies videos that have been in 'processing' status for too long
    (likely due to worker crash, timeout, or other failures) and resets them to 'failed'
    so they can be reprocessed.

    Args:
        stuck_threshold_minutes: Minutes after which a processing video is considered stuck.
                                 Default: 60 minutes (1 hour, matching task_time_limit)

    Returns:
        Dictionary with detection/reset results
    """
    db: Session = SessionLocal()

    try:
        from datetime import datetime, timedelta

        threshold_time = datetime.utcnow() - timedelta(minutes=stuck_threshold_minutes)

        # Find videos stuck in 'processing' status
        stuck_videos = db.query(Video).filter(
            Video.status == "processing",
            Video.updated_at < threshold_time
        ).all()

        reset_count = 0
        reset_video_ids = []
        
        for video in stuck_videos:
            try:
                # Calculate how long it's been stuck
                time_stuck = datetime.utcnow() - (video.updated_at or video.created_at)
                hours_stuck = time_stuck.total_seconds() / 3600

                logger.warning(
                    f"[VIDEO:{video.id}] Detected stuck video - "
                    f"processing for {hours_stuck:.1f} hours, progress: {video.progress}%"
                )

                # Reset to failed status with descriptive error
                video.status = "failed"
                video.error_message = (
                    f"Processing timeout: video was stuck in processing for "
                    f"{hours_stuck:.1f} hours. Last progress: {video.progress}%. "
                    f"You can try reprocessing this video."
                )
                
                reset_count += 1
                reset_video_ids.append(video.id)

            except Exception as e:
                logger.error(f"Error resetting stuck video {video.id}: {e}")

        if reset_count > 0:
            db.commit()
            logger.info(f"Reset {reset_count} stuck videos: {reset_video_ids}")

        return {
            "checked_threshold_minutes": stuck_threshold_minutes,
            "stuck_videos_found": len(stuck_videos),
            "videos_reset": reset_count,
            "reset_video_ids": reset_video_ids,
            "check_time": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Stuck video detection failed: {e}", exc_info=True)
        raise

    finally:
        db.close()


# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    # Run stuck video detection every 15 minutes
    'detect-stuck-videos-every-15-minutes': {
        'task': 'detect_stuck_videos_task',
        'schedule': 900.0,  # 15 minutes in seconds
        'args': (60,),  # stuck_threshold_minutes = 60
    },
    # Run cleanup every 24 hours at midnight
    'cleanup-old-videos-daily': {
        'task': 'cleanup_old_videos_task',
        'schedule': 86400.0,  # 24 hours in seconds
        'args': (7,),  # days_old = 7
    },
}
