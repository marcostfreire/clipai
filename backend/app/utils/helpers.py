"""Helper utility functions."""

import os
import hashlib


def ensure_dir(directory: str) -> str:
    """
    Ensure directory exists, create if not.

    Args:
        directory: Directory path

    Returns:
        Directory path
    """
    os.makedirs(directory, exist_ok=True)
    return directory


def get_file_hash(file_path: str) -> str:
    """
    Calculate SHA256 hash of file.

    Args:
        file_path: Path to file

    Returns:
        Hex digest of hash
    """
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string (e.g., "1:23:45" or "12:34")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"


def format_file_size(bytes: int) -> str:
    """
    Format file size in bytes to human-readable string.

    Args:
        bytes: File size in bytes

    Returns:
        Formatted string (e.g., "1.5 GB", "234 MB")
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024.0:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024.0
    return f"{bytes:.1f} PB"


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing special characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    import re

    # Remove path separators
    filename = os.path.basename(filename)

    # Replace unsafe characters with underscore
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)

    # Remove leading/trailing spaces and dots
    filename = filename.strip(". ")

    return filename


def validate_video_format(file_path: str) -> bool:
    """
    Validate if file is a valid video format.

    Args:
        file_path: Path to file

    Returns:
        True if valid video, False otherwise
    """
    try:
        from ..services.ffmpeg_service import FFmpegService

        ffmpeg = FFmpegService()
        info = ffmpeg.get_video_info(file_path)

        return info.get("duration", 0) > 0

    except Exception:
        return False
