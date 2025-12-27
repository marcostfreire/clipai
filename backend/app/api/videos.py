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
from ..services.auth_service import get_current_user_optional, get_current_user
from ..services.subscription_service import (
    check_video_upload_allowed,
    get_plan_limits,
    get_user_plan,
)
from ..services.storage_service import get_storage_service

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
        
        # Check subscription limits
        limit_check = check_video_upload_allowed(db, current_user)
        if not limit_check["allowed"]:
            raise HTTPException(
                status_code=402,  # Payment Required
                detail={
                    "error": "subscription_limit_reached",
                    "message": limit_check["reason"],
                    "plan": limit_check["plan"],
                    "used": limit_check["used"],
                    "limit": limit_check["limit"],
                    "upgrade_url": limit_check.get("upgrade_url", "/pricing"),
                }
            )
        
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

                # Check duration limit based on user's plan
                plan = get_user_plan(current_user)
                plan_limits = get_plan_limits(plan)
                max_duration_sec = plan_limits["max_video_duration_minutes"] * 60
                
                if duration > max_duration_sec:
                    os.remove(file_path)
                    os.rmdir(video_dir)
                    max_minutes = plan_limits["max_video_duration_minutes"]
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "video_too_long",
                            "message": f"Vídeo muito longo. Máximo permitido no plano {plan.title()}: {max_minutes} minutos",
                            "max_duration_minutes": max_minutes,
                            "video_duration_minutes": round(duration / 60, 1),
                            "plan": plan,
                            "upgrade_url": "/pricing" if plan != "pro" else None,
                        }
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
            
            logger.info(f"[VIDEO:{video_id}] Downloading from URL: {url}")

            ydl_opts = {
                "format": "best[ext=mp4]/best",  # Fallback to any best format
                "outtmpl": file_path,
                "quiet": False,  # Show output for debugging
                "no_warnings": False,
                "extract_flat": False,
                "socket_timeout": 30,
                "retries": 3,
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    logger.info(f"[VIDEO:{video_id}] Starting yt-dlp download...")
                    info = ydl.extract_info(url, download=True)
                    logger.info(f"[VIDEO:{video_id}] Download complete: {info.get('title', 'unknown')}")

                filename = info.get("title", "downloaded_video") + ".mp4"
                
                # Check if file was created
                if not os.path.exists(file_path):
                    raise Exception(f"Download completed but file not found at {file_path}")
                
                file_size = os.path.getsize(file_path)
                logger.info(f"[VIDEO:{video_id}] File size: {file_size / 1024 / 1024:.2f} MB")

                # Get video info
                ffmpeg = FFmpegService()
                video_info = ffmpeg.get_video_info(file_path)
                duration = video_info["duration"]
                logger.info(f"[VIDEO:{video_id}] Duration: {duration:.2f}s")

            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e)
                logger.error(f"[VIDEO:{video_id}] yt-dlp DownloadError: {e}")
                if os.path.exists(video_dir):
                    shutil.rmtree(video_dir)
                
                # Improve error messages for common issues
                if "not made this video available in your country" in error_msg:
                    raise HTTPException(
                        status_code=400, 
                        detail="Este vídeo está bloqueado por região e não pode ser baixado do nosso servidor. Por favor, baixe o vídeo manualmente e faça upload do arquivo."
                    )
                elif "Video unavailable" in error_msg or "Private video" in error_msg:
                    raise HTTPException(
                        status_code=400, 
                        detail="Este vídeo não está disponível. Verifique se o vídeo é público e a URL está correta."
                    )
                elif "Sign in" in error_msg or "age" in error_msg.lower():
                    raise HTTPException(
                        status_code=400, 
                        detail="Este vídeo requer login ou verificação de idade. Por favor, baixe o vídeo manualmente e faça upload do arquivo."
                    )
                else:
                    raise HTTPException(
                        status_code=400, detail=f"Não foi possível baixar o vídeo: {error_msg}"
                    )
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[VIDEO:{video_id}] Error downloading video: {e}", exc_info=True)
                if os.path.exists(video_dir):
                    shutil.rmtree(video_dir)
                
                # Check for geo-restriction in generic exceptions too
                if "not made this video available in your country" in error_msg:
                    raise HTTPException(
                        status_code=400, 
                        detail="Este vídeo está bloqueado por região e não pode ser baixado do nosso servidor. Por favor, baixe o vídeo manualmente e faça upload do arquivo."
                    )
                raise HTTPException(
                    status_code=400, detail=f"Falha ao baixar vídeo: {error_msg}"
                )

        # Create database record
        storage = get_storage_service()
        logger.info(f"[VIDEO:{video_id}] Storage service: use_r2={storage.use_r2}, bucket={storage.r2_bucket_name}")
        
        # Upload to R2 if configured
        if storage.use_r2:
            logger.info(f"[VIDEO:{video_id}] Uploading to R2")
            r2_path = storage.upload_file(file_path, video_id, f"original{file_extension if file else '.mp4'}")
            # Clean up local file after upload
            if os.path.exists(file_path):
                os.remove(file_path)
            # Clean up empty local directory
            if os.path.exists(video_dir) and not os.listdir(video_dir):
                os.rmdir(video_dir)
            file_path = r2_path
            logger.info(f"[VIDEO:{video_id}] Uploaded to R2: {r2_path}")

        video = Video(
            id=video_id,
            user_id=current_user.id if current_user else None,
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

        # Queue processing task with custom parameters
        from ..tasks.celery_tasks import process_video_task

        task = process_video_task.delay(
            video_id,
            clip_min_duration=request.clip_duration_min,
            clip_max_duration=request.clip_duration_max,
            min_virality_score=request.min_score,
        )

        logger.info(f"[VIDEO:{video_id}] Processing task queued: {task.id} (min={request.clip_duration_min}s, max={request.clip_duration_max}s, score>={request.min_score})")

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
