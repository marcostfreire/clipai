"""FFmpeg service for video processing operations."""

import subprocess
import os
import logging
from typing import List, Optional
import json

logger = logging.getLogger(__name__)


class FFmpegService:
    """Service for video processing using FFmpeg."""

    def __init__(self):
        """Initialize FFmpeg service."""
        self.ffmpeg_path = "ffmpeg"
        self.ffprobe_path = "ffprobe"

    def get_video_info(self, video_path: str) -> dict:
        """
        Get video metadata using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with video metadata
        """
        try:
            cmd = [
                self.ffprobe_path,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                video_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)

            # Extract relevant info
            video_stream = next(
                (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
                None,
            )

            return {
                "duration": float(data.get("format", {}).get("duration", 0)),
                "size": int(data.get("format", {}).get("size", 0)),
                "width": video_stream.get("width") if video_stream else 0,
                "height": video_stream.get("height") if video_stream else 0,
                "codec": video_stream.get("codec_name") if video_stream else None,
            }
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            raise

    def extract_frames(
        self, video_path: str, output_dir: str, fps: float = 0.33
    ) -> List[str]:
        """
        Extract frames from video at specified FPS.

        Args:
            video_path: Path to video file
            output_dir: Directory to save frames
            fps: Frames per second to extract (default: 1 frame every 3 seconds)

        Returns:
            List of paths to extracted frames
        """
        try:
            os.makedirs(output_dir, exist_ok=True)

            frame_pattern = os.path.join(output_dir, "frame_%04d.jpg")

            cmd = [
                self.ffmpeg_path,
                "-i",
                video_path,
                "-vf",
                f"fps={fps}",
                "-q:v",
                "2",  # High quality
                frame_pattern,
            ]

            logger.info(f"Extracting frames from {video_path}")
            subprocess.run(cmd, check=True, capture_output=True)

            # Get list of generated frames
            frames = sorted(
                [
                    os.path.join(output_dir, f)
                    for f in os.listdir(output_dir)
                    if f.startswith("frame_") and f.endswith(".jpg")
                ]
            )

            logger.info(f"Extracted {len(frames)} frames")
            return frames

        except Exception as e:
            logger.error(f"Error extracting frames: {e}")
            raise

    def extract_audio(self, video_path: str, output_path: str) -> str:
        """
        Extract audio from video.

        Args:
            video_path: Path to video file
            output_path: Path to save audio file

        Returns:
            Path to extracted audio
        """
        try:
            cmd = [
                self.ffmpeg_path,
                "-i",
                video_path,
                "-vn",  # No video
                "-acodec",
                "pcm_s16le",  # PCM 16-bit
                "-ar",
                "16000",  # 16kHz sample rate (optimal for Whisper)
                "-ac",
                "1",  # Mono
                output_path,
            ]

            logger.info(f"Extracting audio from {video_path}")
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info(f"Audio extracted to {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            raise

    def cut_video(
        self, video_path: str, output_path: str, start_time: float, duration: float
    ) -> str:
        """
        Cut a segment from video.

        Args:
            video_path: Path to source video
            output_path: Path to save cut video
            start_time: Start time in seconds
            duration: Duration in seconds

        Returns:
            Path to cut video
        """
        try:
            cmd = [
                self.ffmpeg_path,
                "-ss",
                str(start_time),
                "-i",
                video_path,
                "-t",
                str(duration),
                "-c",
                "copy",  # Copy codec (fast)
                "-avoid_negative_ts",
                "make_zero",
                output_path,
            ]

            logger.info(f"Cutting video from {start_time}s for {duration}s")
            subprocess.run(cmd, check=True, capture_output=True)

            return output_path

        except Exception as e:
            logger.error(f"Error cutting video: {e}")
            raise

    def convert_to_vertical(
        self, video_path: str, output_path: str, face_position: Optional[float] = 0.5
    ) -> str:
        """
        Convert video to vertical format (9:16).

        Args:
            video_path: Path to source video
            output_path: Path to save vertical video
            face_position: Face position as ratio (0.0=left, 0.5=center, 1.0=right)

        Returns:
            Path to vertical video
        """
        try:
            # Get input video dimensions
            info = self.get_video_info(video_path)
            width = info["width"]
            height = info["height"]

            # Calculate crop parameters for 9:16
            target_aspect = 9 / 16
            crop_width = int(height * target_aspect)

            # Ensure crop width doesn't exceed video width
            if crop_width > width:
                crop_width = width
                crop_height = int(width / target_aspect)
            else:
                crop_height = height

            # Calculate x position based on face position ratio
            # face_position: 0.0 = face at left edge, 0.5 = centered, 1.0 = face at right edge
            # We want to center the crop window on the face position

            # Calculate where face is in pixels
            face_x_pixel = int(width * face_position)

            # Center the crop window on the face
            x_pos = face_x_pixel - (crop_width // 2)

            # Clamp to valid range
            x_pos = max(0, min(x_pos, width - crop_width))

            y_pos = (height - crop_height) // 2

            logger.info(
                f"🎯 CROP CALCULATION: Video {width}x{height} | Face at {face_position:.2f} = {face_x_pixel}px | Crop window: {crop_width}x{crop_height} starting at x={x_pos}"
            )

            # Crop and scale to 1080x1920
            filter_complex = (
                f"crop={crop_width}:{crop_height}:{x_pos}:{y_pos},"
                f"scale=1080:1920:flags=lanczos"
            )

            cmd = [
                self.ffmpeg_path,
                "-i",
                video_path,
                "-vf",
                filter_complex,
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                output_path,
            ]

            logger.info(f"Converting to vertical format: {video_path}")
            subprocess.run(cmd, check=True, capture_output=True)

            return output_path

        except Exception as e:
            logger.error(f"Error converting to vertical: {e}")
            raise

    def add_subtitles(
        self, video_path: str, subtitle_path: str, output_path: str
    ) -> str:
        """
        Add subtitles to video.

        Args:
            video_path: Path to video file
            subtitle_path: Path to subtitle file (ASS format)
            output_path: Path to save video with subtitles

        Returns:
            Path to video with subtitles
        """
        try:
            # Windows FFmpeg path escaping: use double backslashes and escape colons
            subtitle_abs = os.path.abspath(subtitle_path)
            # Escape for ass filter: replace \ with \\ and : with \:
            subtitle_escaped = subtitle_abs.replace("\\", "\\\\\\\\").replace(
                ":", "\\\\:"
            )

            cmd = [
                self.ffmpeg_path,
                "-i",
                video_path,
                "-vf",
                f"ass={subtitle_escaped}",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "copy",
                output_path,
            ]

            logger.info(f"Adding subtitles to {video_path}")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            if result.stderr:
                logger.debug(f"FFmpeg stderr: {result.stderr}")

            return output_path

        except Exception as e:
            logger.error(f"Error adding subtitles: {e}")
            if hasattr(e, "stderr"):
                logger.error(f"FFmpeg stderr: {e.stderr}")
            raise

    def generate_thumbnail(
        self, video_path: str, output_path: str, timestamp: Optional[float] = None
    ) -> str:
        """
        Generate thumbnail from video.

        Args:
            video_path: Path to video file
            output_path: Path to save thumbnail
            timestamp: Timestamp in seconds (if None, use middle of video)

        Returns:
            Path to thumbnail
        """
        try:
            if timestamp is None:
                # Get video duration and use middle
                info = self.get_video_info(video_path)
                timestamp = info["duration"] / 2

            cmd = [
                self.ffmpeg_path,
                "-ss",
                str(timestamp),
                "-i",
                video_path,
                "-vframes",
                "1",
                "-q:v",
                "2",
                output_path,
            ]

            logger.info(f"Generating thumbnail at {timestamp}s")
            subprocess.run(cmd, check=True, capture_output=True)

            return output_path

        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            raise

    def create_subtitle_file(
        self,
        transcript: List[dict],
        output_path: str,
        keywords: Optional[List[str]] = None,
        word_level: bool = True,
        words_per_group: int = 2,
        delay_seconds: float = 0.0,
    ) -> str:
        """
        Create ASS subtitle file from transcript with modern styling.

        Args:
            transcript: List of {start, end, text} or {start, end, word} dictionaries
            output_path: Path to save subtitle file
            keywords: Optional list of keywords to highlight
            word_level: If True, create dynamic word-by-word subtitles (TikTok style)
            words_per_group: Number of words to group together (1-3 recommended)
            delay_seconds: Delay to apply to all subtitles in seconds (negative = earlier, default 0.0s)

        Returns:
            Path to subtitle file
        """
        try:
            # ASS header with modern styling - larger font for word-level
            font_size = 60 if word_level else 48
            ass_content = f"""[Script Info]
Title: ClipAI Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,300,1
Style: Highlight,Arial,{font_size},&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,0,2,10,10,300,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

            keywords_lower = [k.lower() for k in (keywords or [])]

            if word_level and transcript and "word" in transcript[0]:
                # Word-level subtitles (TikTok style)
                logger.info(
                    f"Creating word-level subtitles with {words_per_group} words per group"
                )

                i = 0
                while i < len(transcript):
                    # Group words
                    word_group = []
                    start_time = max(0.0, transcript[i]["start"] + delay_seconds)
                    end_idx = min(i + words_per_group, len(transcript))

                    for j in range(i, end_idx):
                        word = transcript[j]["word"].strip()
                        if word:  # Skip empty words
                            word_group.append(word)

                    if word_group:
                        end_time = max(
                            start_time,
                            transcript[end_idx - 1]["end"] + delay_seconds,
                        )
                        text = " ".join(word_group)

                        # Highlight keywords
                        if keywords_lower:
                            highlighted_words = []
                            for word in word_group:
                                if word.lower().strip(",.!?") in keywords_lower:
                                    highlighted_words.append(
                                        f"{{\\c&H00FFFF&}}{word}{{\\c&HFFFFFF&}}"
                                    )
                                else:
                                    highlighted_words.append(word)
                            text = " ".join(highlighted_words)

                        start_str = self._format_ass_time(start_time)
                        end_str = self._format_ass_time(end_time)
                        ass_content += f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}\n"

                    i = end_idx
            else:
                # Segment-level subtitles (original behavior)
                logger.info("Creating segment-level subtitles")
                for entry in transcript:
                    start_time = self._format_ass_time(
                        max(0.0, entry["start"] + delay_seconds)
                    )
                    end_time = self._format_ass_time(
                        max(0.0, entry["end"] + delay_seconds)
                    )
                    text = entry.get("text", entry.get("word", "")).strip()

                    # Highlight keywords
                    if keywords_lower:
                        words = text.split()
                        highlighted_words = []
                        for word in words:
                            if word.lower().strip(",.!?") in keywords_lower:
                                highlighted_words.append(
                                    f"{{\\c&H00FFFF&}}{word}{{\\c&HFFFFFF&}}"
                                )
                            else:
                                highlighted_words.append(word)
                        text = " ".join(highlighted_words)

                    ass_content += (
                        f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text}\n"
                    )

            # Write to file
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(ass_content)

            logger.info(f"Created subtitle file: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error creating subtitle file: {e}")
            raise

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        """
        Format seconds to ASS time format (H:MM:SS.CC).

        Args:
            seconds: Time in seconds

        Returns:
            Formatted time string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def extract_segment_frames(
        self, video_path: str, output_dir: str, num_frames: int = 5
    ) -> List[str]:
        """
        Extract a specific number of frames evenly distributed across a video segment.

        Args:
            video_path: Path to video segment file
            output_dir: Directory to save frames
            num_frames: Number of frames to extract (default: 5)

        Returns:
            List of paths to extracted frames
        """
        try:
            os.makedirs(output_dir, exist_ok=True)

            # Get video duration
            info = self.get_video_info(video_path)
            duration = info["duration"]

            # Calculate timestamps for evenly distributed frames
            # Add small margin to avoid exceeding video duration
            safe_duration = duration - 0.1  # 0.1s safety margin

            if num_frames == 1:
                timestamps = [safe_duration / 2]
            else:
                interval = safe_duration / (num_frames - 1)
                timestamps = [
                    min(i * interval, safe_duration) for i in range(num_frames)
                ]

            frame_paths = []

            for i, timestamp in enumerate(timestamps):
                frame_path = os.path.join(output_dir, f"segment_frame_{i+1:03d}.jpg")

                cmd = [
                    self.ffmpeg_path,
                    "-ss",
                    str(timestamp),
                    "-i",
                    video_path,
                    "-vframes",
                    "1",
                    "-q:v",
                    "2",
                    frame_path,
                ]

                subprocess.run(cmd, check=True, capture_output=True)
                frame_paths.append(frame_path)

            logger.info(f"Extracted {len(frame_paths)} frames from segment")
            return frame_paths

        except Exception as e:
            logger.error(f"Error extracting segment frames: {e}")
            raise
