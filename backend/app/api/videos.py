"""Video API endpoints."""

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Form
from sqlalchemy.orm import Session
from typing import Optional
import os
import shutil
import logging
from pathlib import Path

from ..database import get_db
from ..models import Video, User
from ..schemas import (
    VideoUploadResponse,
    VideoProcessRequest,
    VideoProcessResponse,
    VideoStatusResponse,
)
from ..config import settings
from ..services.ffmpeg_service import FFmpegService
from ..services.auth_service import get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Upload a video file or provide YouTube URL.

    Args:
        file: Video file (multipart/form-data)
        url: YouTube URL (alternative to file)
        db: Database session

    Returns:
        Video upload response with video_id
    """
    try:
        logger.info(f"Upload request received - file: {file.filename if file else None}, url: {url}")
        
        if not file and not url:
            raise HTTPException(
                status_code=400, detail="Either file or url must be provided"
            )

        if file and url:
            raise HTTPException(
                status_code=400, detail="Provide either file or url, not both"
            )

        # Generate video ID
        import uuid

        video_id = str(uuid.uuid4())

        # Create storage directory
        video_dir = os.path.join(settings.storage_path, video_id)
        os.makedirs(video_dir, exist_ok=True)

        if file:
            # Validate file
            filename = file.filename
            file_extension = Path(filename).suffix.lower()

            allowed_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
            if file_extension not in allowed_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file format. Allowed: {', '.join(allowed_extensions)}",
                )

            # Save file
            file_path = os.path.join(video_dir, f"original{file_extension}")

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Get file size
            file_size = os.path.getsize(file_path)

            # Check size limit
            max_size = settings.max_video_size_mb * 1024 * 1024
            if file_size > max_size:
                os.remove(file_path)
                os.rmdir(video_dir)
                raise HTTPException(
                    status_code=400,
                    detail=f"File too large. Maximum size: {settings.max_video_size_mb}MB",
                )

            # Get video info
            try:
                ffmpeg = FFmpegService()
                video_info = ffmpeg.get_video_info(file_path)
                duration = video_info["duration"]

                # Check duration limit
                if duration > settings.max_video_duration_sec:
                    os.remove(file_path)
                    os.rmdir(video_dir)
                    max_minutes = settings.max_video_duration_sec // 60
                    raise HTTPException(
                        status_code=400,
                        detail=f"Video too long. Maximum duration: {max_minutes} minutes",
                    )

            except Exception as e:
                logger.error(f"Error getting video info: {e}")
                os.remove(file_path)
                os.rmdir(video_dir)
                raise HTTPException(status_code=400, detail="Invalid video file")

        else:
            # Handle YouTube URL
            import yt_dlp

            file_path = os.path.join(video_dir, "original.mp4")

            ydl_opts = {
                "format": "best[ext=mp4]",
                "outtmpl": file_path,
                "quiet": True,
                "no_warnings": True,
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                filename = "downloaded_video.mp4"
                file_size = os.path.getsize(file_path)

                # Get video info
                ffmpeg = FFmpegService()
                video_info = ffmpeg.get_video_info(file_path)
                duration = video_info["duration"]

            except Exception as e:
                logger.error(f"Error downloading YouTube video: {e}")
                if os.path.exists(video_dir):
                    shutil.rmtree(video_dir)
                raise HTTPException(
                    status_code=400, detail=f"Failed to download video: {str(e)}"
                )

        # Create database record
        video = Video(
            id=video_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            duration=duration,
            status="queued",
            progress=0,
        )

        db.add(video)
        db.commit()
        db.refresh(video)

        logger.info(f"[VIDEO:{video_id}] Uploaded successfully: {filename}")

        return VideoUploadResponse(
            video_id=video_id, status="queued", message="Video uploaded successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/upload/chunk")
async def upload_chunk(
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    filename: str = Form(...),
    upload_id: str = Form(...),
    chunk: UploadFile = File(...),
):
    """Upload a single chunk of a video file."""
    try:
        # Create temp directory for this upload
        temp_dir = os.path.join(settings.storage_path, ".chunks", upload_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Save chunk
        chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
        with open(chunk_path, "wb") as f:
            shutil.copyfileobj(chunk.file, f)
        
        logger.info(f"Chunk {chunk_index + 1}/{total_chunks} saved for {upload_id}")
        
        return {
            "success": True,
            "chunk_index": chunk_index,
            "upload_id": upload_id
        }
    except Exception as e:
        logger.error(f"Error uploading chunk: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload/complete", response_model=VideoUploadResponse)
async def complete_chunked_upload(
    upload_id: str = Form(...),
    filename: str = Form(...),
    total_chunks: int = Form(...),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Combine all chunks into final video file."""
    try:
        temp_dir = os.path.join(settings.storage_path, ".chunks", upload_id)
        
        # Verify all chunks exist
        for i in range(total_chunks):
            chunk_path = os.path.join(temp_dir, f"chunk_{i}")
            if not os.path.exists(chunk_path):
                raise HTTPException(status_code=400, detail=f"Missing chunk {i}")
        
        # Generate video ID and create directory
        import uuid
        video_id = str(uuid.uuid4())
        video_dir = os.path.join(settings.storage_path, video_id)
        os.makedirs(video_dir, exist_ok=True)
        
        # Combine chunks
        file_extension = Path(filename).suffix.lower()
        file_path = os.path.join(video_dir, f"original{file_extension}")
        
        with open(file_path, "wb") as outfile:
            for i in range(total_chunks):
                chunk_path = os.path.join(temp_dir, f"chunk_{i}")
                with open(chunk_path, "rb") as infile:
                    shutil.copyfileobj(infile, outfile)
        
        # Clean up chunks
        shutil.rmtree(temp_dir)
        
        # Get video info
        ffmpeg = FFmpegService()
        video_info = ffmpeg.get_video_info(file_path)
        duration = video_info.get('duration', 0)
        
        # Create database entry
        video = Video(
            id=video_id,
            filename=filename,
            file_path=file_path,
            duration=duration,
            status="uploaded",
            user_id=current_user.id if current_user else None,
        )
        db.add(video)
        db.commit()
        
        logger.info(f"Chunked upload complete: {video_id}")
        
        return VideoUploadResponse(
            video_id=video_id,
            filename=filename,
            duration=duration,
            status="uploaded",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing chunked upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{video_id}/process", response_model=VideoProcessResponse)
async def process_video(
    video_id: str,
    request: VideoProcessRequest = VideoProcessRequest(),
    db: Session = Depends(get_db),
):
    """
    Start video processing.

    Args:
        video_id: Video ID
        request: Processing parameters
        db: Database session

    Returns:
        Processing response with job_id
    """
    try:
        # Get video
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        if video.status == "processing":
            raise HTTPException(
                status_code=400, detail="Video is already being processed"
            )

        if video.status == "completed":
            raise HTTPException(status_code=400, detail="Video already processed")

        # Queue processing task
        from ..tasks.celery_tasks import process_video_task

        task = process_video_task.delay(video_id)

        logger.info(f"[VIDEO:{video_id}] Processing task queued: {task.id}")

        return VideoProcessResponse(job_id=task.id, video_id=video_id, status="queued")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error queuing video processing: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to queue processing: {str(e)}"
        )


@router.get("/{video_id}/status", response_model=VideoStatusResponse)
async def get_video_status(video_id: str, db: Session = Depends(get_db)):
    """
    Get video processing status.

    Args:
        video_id: Video ID
        db: Database session

    Returns:
        Video status response
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        return VideoStatusResponse(
            video_id=video.id,
            status=video.status,
            progress=video.progress,
            error_message=video.error_message,
            created_at=video.created_at,
            updated_at=video.updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting video status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get status")


@router.delete("/{video_id}")
async def delete_video(video_id: str, db: Session = Depends(get_db)):
    """
    Delete video and all associated clips.

    Args:
        video_id: Video ID
        db: Database session

    Returns:
        Success message
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Delete files
        video_dir = os.path.join(settings.storage_path, video_id)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)

        # Delete from database (cascade will delete clips)
        db.delete(video)
        db.commit()

        logger.info(f"[VIDEO:{video_id}] Deleted successfully")

        return {"message": "Video deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting video: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete video")
