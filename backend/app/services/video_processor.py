"""Video processor service - orchestrates the video processing pipeline."""

import logging
import os
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Orchestrates the complete video processing pipeline."""

    def __init__(
        self,
        ffmpeg_service,
        ai_service,  # GeminiService
        whisper_service,
        storage_path: str,
        frames_per_second: float = 0.1,  # Optimized: 1 frame every 10 seconds
        clip_min_duration: int = 30,
        clip_max_duration: int = 60,
        min_virality_score: float = 5.0,
        subtitle_delay_seconds: float = 0.0,
    ):
        """
        Initialize video processor.

        Args:
            ffmpeg_service: FFmpeg service instance
            ai_service: AI service instance (GeminiService)
            whisper_service: Whisper service instance
            storage_path: Base storage path
            frames_per_second: FPS for frame extraction
            clip_min_duration: Minimum clip duration
            clip_max_duration: Maximum clip duration
            min_virality_score: Minimum virality score threshold
            subtitle_delay_seconds: Optional global shift applied to subtitles
        """
        self.ffmpeg = ffmpeg_service
        self.ai = ai_service
        self.whisper = whisper_service
        self.storage_path = storage_path
        self.fps = frames_per_second
        self.clip_min_duration = clip_min_duration
        self.clip_max_duration = clip_max_duration
        self.min_virality_score = min_virality_score
        self.subtitle_delay_seconds = subtitle_delay_seconds

    def calculate_combined_score(
        self,
        timestamp: float,
        frame_analyses: Dict[float, dict],
        viral_moments: List[dict],
        sentiment_data: Optional[dict] = None,
    ) -> float:
        """
        Calculate final virality score combining multiple signals.

        Args:
            timestamp: Timestamp to score
            frame_analyses: Dictionary of frame analysis results
            viral_moments: List of identified viral moments
            sentiment_data: Optional sentiment analysis data

        Returns:
            Combined score (0-10)
        """
        # Find closest frame analysis
        closest_timestamp = min(
            frame_analyses.keys(), key=lambda t: abs(t - timestamp), default=None
        )
        visual_score = 5.0

        if closest_timestamp is not None:
            frame_data = frame_analyses[closest_timestamp]
            visual_score = frame_data.get("engagement_score", 5.0)

        # Check if timestamp is within any viral moment
        moment_score = 0.0
        for moment in viral_moments:
            if moment["start_time"] <= timestamp <= moment["end_time"]:
                moment_score = moment.get("virality_score", 0.0)
                break

        # Sentiment score
        audio_score = (
            sentiment_data.get("engagement_score", 5.0) if sentiment_data else 5.0
        )

        # Weighted combination: 30% visual, 30% audio, 40% content
        final_score = (visual_score * 0.3) + (audio_score * 0.3) + (moment_score * 0.4)

        return round(final_score, 2)

    def select_best_segments(
        self,
        frame_analyses: Dict[float, dict],
        viral_moments: List[dict],
        transcript: List[Dict],
        video_duration: float,
        word_level_transcript: List[Dict] = None,
        top_n: int = 3,
    ) -> List[Dict]:
        """
        Select best video segments for clipping.

        Args:
            frame_analyses: Frame analysis results
            viral_moments: Identified viral moments
            transcript: Full transcript
            video_duration: Total video duration
            top_n: Number of segments to select

        Returns:
            List of selected segments with metadata
        """
        segments = []

        # Start with viral moments as candidates
        for moment in viral_moments:
            start_time = moment["start_time"]
            end_time = moment["end_time"]
            duration = end_time - start_time

            # Adjust duration if needed
            if duration < self.clip_min_duration:
                # Extend segment
                extend = (self.clip_min_duration - duration) / 2
                start_time = max(0, start_time - extend)
                end_time = min(video_duration, end_time + extend)
            elif duration > self.clip_max_duration:
                # Truncate to max duration
                end_time = start_time + self.clip_max_duration

            # Adjust to sentence boundaries
            adjusted_start, adjusted_end = self.whisper.find_sentence_boundaries(
                transcript, start_time, end_time
            )

            # Validate duration is positive
            if adjusted_end <= adjusted_start:
                logger.warning(
                    f"Invalid segment: end ({adjusted_end}) <= start ({adjusted_start}), skipping"
                )
                continue

            # Ensure minimum duration
            duration = adjusted_end - adjusted_start
            if duration < self.clip_min_duration:
                # Try to extend equally
                extend = (self.clip_min_duration - duration) / 2
                adjusted_start = max(0, adjusted_start - extend)
                adjusted_end = min(video_duration, adjusted_end + extend)

                # If still too short, skip
                if adjusted_end - adjusted_start < self.clip_min_duration:
                    logger.warning(
                        f"Segment too short after adjustment ({adjusted_end - adjusted_start}s), skipping"
                    )
                    continue

            # Calculate average score for this segment
            mid_timestamp = (adjusted_start + adjusted_end) / 2
            score = self.calculate_combined_score(
                mid_timestamp, frame_analyses, viral_moments
            )

            # Get transcript for this segment
            segment_transcript = self.whisper.extract_segment_transcript(
                transcript, adjusted_start, adjusted_end
            )

            # Extract word-level transcript for this segment (for dynamic subtitles)
            segment_words = []
            if word_level_transcript:
                segment_duration = adjusted_end - adjusted_start
                for word in word_level_transcript:
                    # Include word if it overlaps segment in any way
                    if word["end"] < adjusted_start or word["start"] > adjusted_end:
                        continue

                    relative_start = max(0.0, word["start"] - adjusted_start)
                    relative_end = max(
                        relative_start,
                        min(segment_duration, word["end"] - adjusted_start),
                    )

                    segment_words.append(
                        {
                            "start": relative_start,
                            "end": relative_end,
                            "absolute_start": word["start"],
                            "absolute_end": word["end"],
                            "word": word["word"],
                        }
                    )

            segments.append(
                {
                    "start_time": adjusted_start,
                    "end_time": adjusted_end,
                    "duration": adjusted_end - adjusted_start,
                    "virality_score": score,
                    "transcript": segment_transcript,
                    "word_transcript": segment_words,
                    "keywords": moment.get("keywords", []),
                    "hook_type": moment.get("hook_type", "insight"),
                    "reason": moment.get("reason", ""),
                    "analysis_data": moment,
                }
            )

        # Sort by score and select top N
        segments.sort(key=lambda x: x["virality_score"], reverse=True)
        selected = segments[:top_n]

        # Log all segments before filtering for debugging
        logger.info(f"📊 All {len(segments)} segments before filtering:")
        for i, s in enumerate(segments):
            logger.info(f"  [{i+1}] Score: {s['virality_score']:.2f}, Time: {s['start_time']:.1f}s-{s['end_time']:.1f}s, Reason: {s.get('reason', 'N/A')[:50]}")

        # Filter by minimum score
        selected = [
            s for s in selected if s["virality_score"] >= self.min_virality_score
        ]

        # Log filtering result
        filtered_count = len(segments[:top_n]) - len(selected)
        if filtered_count > 0:
            logger.warning(f"⚠️ Filtered out {filtered_count} segments with scores < {self.min_virality_score}")

        logger.info(
            f"✅ Selected {len(selected)} segments with scores >= {self.min_virality_score}"
        )

        return selected

    def _analyze_segment_faces(
        self, video_path: str, clip_id: str, num_frames: int = 5
    ) -> List[dict]:
        """
        Analyze faces in a video segment by extracting and analyzing frames.

        Args:
            video_path: Path to video segment file
            clip_id: Clip ID for temporary directory
            num_frames: Number of frames to extract and analyze

        Returns:
            List of frame analysis results
        """
        temp_frames_dir = None
        try:
            # Create temporary directory for frames
            temp_frames_dir = os.path.join(
                os.path.dirname(video_path), f"{clip_id}_temp_frames"
            )
            os.makedirs(temp_frames_dir, exist_ok=True)

            # Extract frames from segment
            logger.info(
                f"[CLIP:{clip_id}] Extracting {num_frames} frames for face analysis"
            )
            frame_paths = self.ffmpeg.extract_segment_frames(
                video_path, temp_frames_dir, num_frames=num_frames
            )

            # Analyze each frame
            analyses = []
            for i, frame_path in enumerate(frame_paths):
                logger.debug(f"[CLIP:{clip_id}] Analyzing frame {i+1}/{num_frames}")
                analysis = self.ai.analyze_frame(frame_path)
                analyses.append(analysis)

            logger.info(
                f"[CLIP:{clip_id}] Completed face analysis of {len(analyses)} frames"
            )
            return analyses

        except Exception as e:
            logger.error(f"[CLIP:{clip_id}] Error analyzing segment faces: {e}")
            return []
        finally:
            # Clean up temporary frames
            if temp_frames_dir and os.path.exists(temp_frames_dir):
                import shutil

                shutil.rmtree(temp_frames_dir, ignore_errors=True)
                logger.debug(f"[CLIP:{clip_id}] Cleaned up temporary frames")

    def _determine_crop_strategy(
        self, frame_analyses: List[dict], threshold: float = 0.7
    ) -> float:
        """
        Determine crop position based on face analysis results.

        Args:
            frame_analyses: List of frame analysis results
            threshold: Minimum proportion of frames with single face (default: 0.7 = 70%)

        Returns:
            Face position as percentage (0.0-1.0), or 0.5 for centered crop
        """
        if not frame_analyses:
            return 0.5  # Center

        # Count frames with exactly 1 face and valid position
        single_face_frames = [
            a
            for a in frame_analyses
            if a.get("face_count") == 1 and a.get("face_position_x") is not None
        ]

        total_frames = len(frame_analyses)
        single_face_ratio = len(single_face_frames) / total_frames

        logger.debug(
            f"Single face ratio: {single_face_ratio:.2%} ({len(single_face_frames)}/{total_frames})"
        )

        # If >70% frames have exactly 1 face, calculate average position
        if single_face_ratio > threshold:
            # Get all face positions as percentages (0-100)
            positions = [a["face_position_x"] for a in single_face_frames]
            # Calculate average position
            avg_position = sum(positions) / len(positions)
            # Convert to 0.0-1.0 range
            position_ratio = avg_position / 100.0

            logger.info(
                f"Using face-based crop at {avg_position:.1f}% ({position_ratio:.2f}) - ratio: {single_face_ratio:.2%}"
            )
            return position_ratio
        else:
            logger.info(
                f"Using centered crop (single face ratio {single_face_ratio:.2%} < {threshold:.2%})"
            )
            return 0.5  # Center

    def generate_clip(
        self, video_path: str, segment: Dict, output_dir: str, clip_id: str
    ) -> Dict:
        """
        Generate a single clip from segment data.

        Args:
            video_path: Path to source video
            segment: Segment metadata
            output_dir: Output directory
            clip_id: Unique clip ID

        Returns:
            Dictionary with clip file paths
        """
        try:
            os.makedirs(output_dir, exist_ok=True)

            # Step 1: Cut video segment
            temp_cut = os.path.join(output_dir, f"{clip_id}_temp_cut.mp4")
            self.ffmpeg.cut_video(
                video_path, temp_cut, segment["start_time"], segment["duration"]
            )
            logger.info(f"[CLIP:{clip_id}] Video segment cut")

            # Step 1.5: Analyze segment for optimal crop position
            logger.info(f"[CLIP:{clip_id}] Analyzing segment for face detection")
            segment_analyses = self._analyze_segment_faces(
                temp_cut, clip_id, num_frames=5
            )
            crop_position = self._determine_crop_strategy(
                segment_analyses, threshold=0.7
            )
            logger.info(f"[CLIP:{clip_id}] Selected crop position: {crop_position}")

            # Step 2: Convert to vertical
            temp_vertical = os.path.join(output_dir, f"{clip_id}_temp_vertical.mp4")
            self.ffmpeg.convert_to_vertical(
                temp_cut, temp_vertical, face_position=crop_position
            )
            logger.info(f"[CLIP:{clip_id}] Converted to vertical format")

            # Step 3: Create subtitle file
            subtitle_file = os.path.join(output_dir, f"{clip_id}_subs.ass")

            # Use word-level transcript if available, otherwise use regular transcript
            subtitle_transcript = segment.get("word_transcript", [])
            if subtitle_transcript:
                logger.info(
                    f"[CLIP:{clip_id}] Creating dynamic word-level subtitles ({len(subtitle_transcript)} words)"
                )
                self.ffmpeg.create_subtitle_file(
                    subtitle_transcript,
                    subtitle_file,
                    keywords=segment.get("keywords", []),
                    word_level=True,
                    words_per_group=2,  # 2 words at a time for better readability
                    delay_seconds=self.subtitle_delay_seconds,
                )
            else:
                logger.info(
                    f"[CLIP:{clip_id}] Creating segment-level subtitles (fallback)"
                )
                self.ffmpeg.create_subtitle_file(
                    segment["transcript"],
                    subtitle_file,
                    keywords=segment.get("keywords", []),
                    word_level=False,
                    delay_seconds=self.subtitle_delay_seconds,
                )
            logger.info(f"[CLIP:{clip_id}] Subtitles created")

            # Step 4: Add subtitles to video
            final_video = os.path.join(output_dir, f"{clip_id}_final.mp4")
            self.ffmpeg.add_subtitles(temp_vertical, subtitle_file, final_video)
            logger.info(f"[CLIP:{clip_id}] Subtitles added to video")

            # Step 5: Generate thumbnail
            thumbnail = os.path.join(output_dir, f"{clip_id}_thumb.jpg")
            self.ffmpeg.generate_thumbnail(
                final_video, thumbnail, timestamp=segment["duration"] / 2
            )
            logger.info(f"[CLIP:{clip_id}] Thumbnail generated")

            # Clean up temporary files
            for temp_file in [temp_cut, temp_vertical]:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            return {
                "video_path": final_video,
                "thumbnail_path": thumbnail,
                "subtitle_path": subtitle_file,
            }

        except Exception as e:
            logger.error(f"[CLIP:{clip_id}] Error generating clip: {e}")
            raise

    def process_video(
        self, video_id: str, video_path: str, progress_callback=None
    ) -> List[Dict]:
        """
        Process entire video and generate clips.

        Args:
            video_id: Video ID
            video_path: Path to video file
            progress_callback: Optional callback for progress updates

        Returns:
            List of clip metadata dictionaries
        """
        import time

        try:
            pipeline_start = time.time()
            logger.info(f"[VIDEO:{video_id}] Starting processing pipeline")
            logger.info(
                f"[VIDEO:{video_id}] Configuration: FPS={self.fps} (1 frame every {1/self.fps:.0f}s)"
            )

            # Create directories
            video_dir = os.path.join(self.storage_path, video_id)
            frames_dir = os.path.join(video_dir, "frames")
            clips_dir = os.path.join(video_dir, "clips")
            os.makedirs(frames_dir, exist_ok=True)
            os.makedirs(clips_dir, exist_ok=True)

            # Get video info
            video_info = self.ffmpeg.get_video_info(video_path)
            video_duration = video_info["duration"]
            logger.info(f"[VIDEO:{video_id}] Duration: {video_duration:.1f}s")

            # Step 1: Extract frames
            if progress_callback:
                progress_callback(10, "Extracting frames")
            logger.info(f"[VIDEO:{video_id}] Step 1/10: Extracting frames")
            frames = self.ffmpeg.extract_frames(video_path, frames_dir, fps=self.fps)
            logger.info(f"[VIDEO:{video_id}] Extracted {len(frames)} frames")

            # Step 2: Analyze frames with AI
            if progress_callback:
                progress_callback(25, "Analyzing visual content")
            logger.info(f"[VIDEO:{video_id}] Step 2/10: Analyzing frames")
            frame_analyses = self.ai.batch_analyze_frames(frames, fps=self.fps)
            logger.info(f"[VIDEO:{video_id}] Analyzed {len(frame_analyses)} frames")

            # Step 3: Extract audio
            if progress_callback:
                progress_callback(40, "Extracting audio")
            logger.info(f"[VIDEO:{video_id}] Step 3/10: Extracting audio")
            audio_path = os.path.join(video_dir, "audio.wav")
            self.ffmpeg.extract_audio(video_path, audio_path)

            # Step 4: Transcribe with Whisper
            if progress_callback:
                progress_callback(55, "Transcribing audio")
            logger.info(f"[VIDEO:{video_id}] Step 4/10: Transcribing audio")
            transcription = self.whisper.transcribe(audio_path)
            transcript = self.whisper.format_transcript_with_timestamps(transcription)
            full_text = self.whisper.get_full_text(transcript)
            # Extract word-level timestamps for dynamic subtitles
            word_level_transcript = self.whisper.get_word_level_transcript(
                transcription
            )
            logger.info(
                f"[VIDEO:{video_id}] Transcription completed: {len(transcript)} segments, {len(word_level_transcript)} words"
            )

            # Step 5: Identify viral moments
            if progress_callback:
                progress_callback(70, "Identifying viral moments")
            logger.info(f"[VIDEO:{video_id}] Step 5/10: Identifying viral moments")
            viral_moments = self.ai.identify_viral_moments(full_text, video_duration)
            logger.info(
                f"[VIDEO:{video_id}] Identified {len(viral_moments)} viral moments"
            )

            # Step 6: Select best segments
            if progress_callback:
                progress_callback(75, "Selecting best segments")
            logger.info(f"[VIDEO:{video_id}] Step 6/10: Selecting segments")
            segments = self.select_best_segments(
                frame_analyses,
                viral_moments,
                transcript,
                video_duration,
                word_level_transcript,
            )
            logger.info(f"[VIDEO:{video_id}] Selected {len(segments)} segments")

            # Step 7-10: Generate clips
            clips_metadata = []
            for i, segment in enumerate(segments):
                clip_progress = 75 + (i + 1) * (25 // len(segments))
                if progress_callback:
                    progress_callback(
                        clip_progress, f"Generating clip {i+1}/{len(segments)}"
                    )

                logger.info(f"[VIDEO:{video_id}] Generating clip {i+1}/{len(segments)}")

                clip_id = f"{video_id}_clip_{i+1}"
                clip_files = self.generate_clip(video_path, segment, clips_dir, clip_id)

                # Get transcript text
                transcript_text = " ".join([t["text"] for t in segment["transcript"]])

                clips_metadata.append(
                    {
                        "clip_id": clip_id,
                        "start_time": segment["start_time"],
                        "end_time": segment["end_time"],
                        "duration": segment["duration"],
                        "virality_score": segment["virality_score"],
                        "transcript": transcript_text,
                        "keywords": segment["keywords"],
                        "file_path": clip_files["video_path"],
                        "thumbnail_path": clip_files["thumbnail_path"],
                        "analysis_data": segment["analysis_data"],
                    }
                )

            if progress_callback:
                progress_callback(100, "Processing completed")

            pipeline_time = time.time() - pipeline_start
            logger.info(
                f"[VIDEO:{video_id}] Processing completed. Generated {len(clips_metadata)} clips"
            )
            logger.info(f"[VIDEO:{video_id}] 📊 PERFORMANCE REPORT:")
            logger.info(
                f"[VIDEO:{video_id}]   ⏱️  Total time: {pipeline_time:.2f}s ({pipeline_time/60:.1f} min)"
            )
            logger.info(
                f"[VIDEO:{video_id}]   🎬 Video duration: {video_duration:.1f}s"
            )
            logger.info(
                f"[VIDEO:{video_id}]   📈 Processing ratio: {pipeline_time/video_duration:.2f}x real-time"
            )
            logger.info(
                f"[VIDEO:{video_id}]   💰 Estimated GPU cost: R$ {(pipeline_time/3600)*1.25:.2f}"
            )

            return clips_metadata

        except Exception as e:
            logger.error(
                f"[VIDEO:{video_id}] Error in processing pipeline: {e}", exc_info=True
            )
            raise
