"""Clips API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
import os
import logging

from ..database import get_db
from ..models import Video, Clip
from ..schemas import ClipResponse, ClipsListResponse
from ..services.storage_service import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["clips"])


@router.get("/{video_id}/clips", response_model=ClipsListResponse)
async def get_video_clips(
    video_id: str, min_score: float = 0.0, db: Session = Depends(get_db)
):
    """
    Get all clips for a video.

    Args:
        video_id: Video ID
        min_score: Minimum virality score filter
        db: Database session

    Returns:
        List of clips
    """
    try:
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")

        # Query clips
        clips = (
            db.query(Clip)
            .filter(Clip.video_id == video_id, Clip.virality_score >= min_score)
            .order_by(Clip.virality_score.desc())
            .all()
        )

        # Format response
        clips_response = []
        for clip in clips:
            clips_response.append(
                ClipResponse(
                    clip_id=clip.id,
                    start_time=clip.start_time,
                    end_time=clip.end_time,
                    duration=clip.duration,
                    virality_score=clip.virality_score,
                    transcript=clip.transcript,
                    keywords=clip.keywords,
                    thumbnail_url=f"/api/clips/{clip.id}/thumbnail",
                    download_url=f"/api/clips/{clip.id}/download",
                    created_at=clip.created_at,
                )
            )

        return ClipsListResponse(
            video_id=video_id, clips=clips_response, total=len(clips_response)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clips: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get clips")


@router.get("/{video_id}/clips/{clip_id}", response_model=ClipResponse)
async def get_clip(video_id: str, clip_id: str, db: Session = Depends(get_db)):
    """
    Get specific clip details.

    Args:
        video_id: Video ID
        clip_id: Clip ID
        db: Database session

    Returns:
        Clip details
    """
    try:
        clip = (
            db.query(Clip).filter(Clip.id == clip_id, Clip.video_id == video_id).first()
        )

        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")

        return ClipResponse(
            clip_id=clip.id,
            start_time=clip.start_time,
            end_time=clip.end_time,
            duration=clip.duration,
            virality_score=clip.virality_score,
            transcript=clip.transcript,
            keywords=clip.keywords,
            thumbnail_url=f"/api/clips/{clip.id}/thumbnail",
            download_url=f"/api/clips/{clip.id}/download",
            created_at=clip.created_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clip: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get clip")


# Separate router for clip-specific endpoints
clips_router = APIRouter(prefix="/clips", tags=["clips"])


@clips_router.get("/{clip_id}/download")
async def download_clip(clip_id: str, db: Session = Depends(get_db)):
    """
    Download clip video file.

    Args:
        clip_id: Clip ID
        db: Database session

    Returns:
        Video file or redirect to R2 URL
    """
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")

        storage = get_storage_service()
        
        # If using R2 and path is R2 URL, redirect to it
        if storage.use_r2 and storage.is_r2_path(clip.file_path):
            # Get presigned or public URL
            url = storage.get_presigned_url(clip.file_path, expires_in=3600)
            return RedirectResponse(url=url, status_code=302)

        # Local file
        if not os.path.exists(clip.file_path):
            raise HTTPException(status_code=404, detail="Clip file not found")

        filename = f"clip_{clip_id}.mp4"

        return FileResponse(clip.file_path, media_type="video/mp4", filename=filename)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading clip: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to download clip")


@clips_router.get("/{clip_id}/thumbnail")
async def get_clip_thumbnail(clip_id: str, db: Session = Depends(get_db)):
    """
    Get clip thumbnail image.

    Args:
        clip_id: Clip ID
        db: Database session

    Returns:
        Thumbnail image or redirect to R2 URL
    """
    try:
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            raise HTTPException(status_code=404, detail="Clip not found")

        if not clip.thumbnail_path:
            raise HTTPException(status_code=404, detail="Thumbnail not found")

        storage = get_storage_service()
        
        # If using R2 and path is R2 URL, redirect to it
        if storage.use_r2 and storage.is_r2_path(clip.thumbnail_path):
            url = storage.get_presigned_url(clip.thumbnail_path, expires_in=3600)
            return RedirectResponse(url=url, status_code=302)

        # Local file
        if not os.path.exists(clip.thumbnail_path):
            raise HTTPException(status_code=404, detail="Thumbnail not found")

        return FileResponse(clip.thumbnail_path, media_type="image/jpeg")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting thumbnail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to get thumbnail")
