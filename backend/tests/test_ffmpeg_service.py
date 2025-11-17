"""
Unit tests for FFmpeg service.
"""

import pytest
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from app.services.ffmpeg_service import FFmpegService
from app.config import Settings


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        storage_path="./test_storage", min_clip_duration=15, max_clip_duration=60
    )


@pytest.fixture
def ffmpeg_service(settings):
    """Create FFmpeg service instance."""
    return FFmpegService(settings)


@pytest.fixture
def test_video_path(tmp_path):
    """Create a dummy test video file."""
    video_file = tmp_path / "test_video.mp4"
    video_file.write_text("fake video content")
    return str(video_file)


class TestFFmpegService:
    """Test FFmpeg service functionality."""

    def test_format_ass_time(self, ffmpeg_service):
        """Test ASS timestamp formatting."""
        result = ffmpeg_service.format_ass_time(65.5)
        assert result == "0:01:05.50"

        result = ffmpeg_service.format_ass_time(3725.123)
        assert result == "1:02:05.12"

    @patch("subprocess.run")
    def test_get_video_info(self, mock_run, ffmpeg_service, test_video_path):
        """Test video info extraction."""
        mock_run.return_value = Mock(
            stdout='{"streams": [{"width": 1920, "height": 1080, "duration": "120.5"}], "format": {"duration": "120.5"}}',
            returncode=0,
        )

        info = ffmpeg_service.get_video_info(test_video_path)

        assert info["width"] == 1920
        assert info["height"] == 1080
        assert info["duration"] == 120.5

    @patch("subprocess.run")
    def test_extract_frames(self, mock_run, ffmpeg_service, test_video_path, tmp_path):
        """Test frame extraction."""
        mock_run.return_value = Mock(returncode=0)

        output_dir = str(tmp_path / "frames")
        result = ffmpeg_service.extract_frames(test_video_path, output_dir, fps=1)

        assert result == output_dir
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_extract_audio(self, mock_run, ffmpeg_service, test_video_path, tmp_path):
        """Test audio extraction."""
        mock_run.return_value = Mock(returncode=0)

        output_path = str(tmp_path / "audio.mp3")
        result = ffmpeg_service.extract_audio(test_video_path, output_path)

        assert result == output_path
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_cut_video(self, mock_run, ffmpeg_service, test_video_path, tmp_path):
        """Test video cutting."""
        mock_run.return_value = Mock(returncode=0)

        output_path = str(tmp_path / "clip.mp4")
        result = ffmpeg_service.cut_video(
            test_video_path, output_path, start_time=10.0, duration=30.0
        )

        assert result == output_path
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_convert_to_vertical(
        self, mock_run, ffmpeg_service, test_video_path, tmp_path
    ):
        """Test vertical video conversion."""
        mock_run.return_value = Mock(returncode=0)

        output_path = str(tmp_path / "vertical.mp4")
        result = ffmpeg_service.convert_to_vertical(test_video_path, output_path)

        assert result == output_path
        mock_run.assert_called_once()

    def test_create_subtitle_file(self, ffmpeg_service, tmp_path):
        """Test subtitle file creation."""
        subtitles = [
            {"start": 0.0, "end": 2.5, "text": "Hello world"},
            {"start": 2.5, "end": 5.0, "text": "Testing subtitles"},
        ]

        output_path = str(tmp_path / "subtitles.ass")
        result = ffmpeg_service.create_subtitle_file(subtitles, output_path)

        assert result == output_path
        assert os.path.exists(output_path)

        # Verify content
        with open(output_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Hello world" in content
            assert "Testing subtitles" in content

    @patch("subprocess.run")
    def test_add_subtitles(self, mock_run, ffmpeg_service, test_video_path, tmp_path):
        """Test adding subtitles to video."""
        mock_run.return_value = Mock(returncode=0)

        subtitles = [{"start": 0.0, "end": 2.5, "text": "Test"}]
        output_path = str(tmp_path / "with_subs.mp4")

        result = ffmpeg_service.add_subtitles(test_video_path, output_path, subtitles)

        assert result == output_path
        mock_run.assert_called()

    @patch("subprocess.run")
    def test_generate_thumbnail(
        self, mock_run, ffmpeg_service, test_video_path, tmp_path
    ):
        """Test thumbnail generation."""
        mock_run.return_value = Mock(returncode=0)

        output_path = str(tmp_path / "thumb.jpg")
        result = ffmpeg_service.generate_thumbnail(
            test_video_path, output_path, timestamp=10.0
        )

        assert result == output_path
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_ffmpeg_error_handling(self, mock_run, ffmpeg_service, test_video_path):
        """Test FFmpeg error handling."""
        mock_run.return_value = Mock(returncode=1, stderr="FFmpeg error message")

        with pytest.raises(Exception) as exc_info:
            ffmpeg_service.extract_frames(test_video_path, "/tmp/frames")

        assert "FFmpeg error" in str(exc_info.value)
