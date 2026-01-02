"""Whisper service for audio transcription."""

from faster_whisper import WhisperModel
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class WhisperService:
    """Service for audio transcription using Faster-Whisper."""

    def __init__(
        self, model_name: str = "small", device: str = "cpu", compute_type: str = "int8"
    ):
        """
        Initialize Whisper service.

        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large-v3)
                       Default: small (good balance of speed/accuracy for Railway Hobby)
            device: Device to run on ("cpu" or "cuda")
                   Default: cpu (Railway Hobby has no GPU)
            compute_type: Compute type ("int8", "float16", "int8_float16")
                         Default: int8 (optimized for CPU, lower memory)
        """
        logger.info(
            f"Loading Faster-Whisper model: {model_name} on {device} with {compute_type}"
        )
        self.model = WhisperModel(model_name, device=device, compute_type=compute_type)
        logger.info("Faster-Whisper model loaded successfully")

    def transcribe(self, audio_path: str, language: str = "pt") -> Dict:
        """
        Transcribe audio file with word-level timestamps.

        Args:
            audio_path: Path to audio file
            language: Language code (default: pt for Portuguese)

        Returns:
            Dictionary with transcription results (compatible with openai-whisper format)
        """
        try:
            logger.info(f"Transcribing audio: {audio_path}")

            # Faster-Whisper returns a generator of segments and info
            segments_generator, info = self.model.transcribe(
                audio_path, language=language, word_timestamps=True, beam_size=5
            )

            # Convert generator to list and format to match openai-whisper output
            segments_list = []
            for segment in segments_generator:
                segment_dict = {
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                    "avg_logprob": segment.avg_logprob,
                    "no_speech_prob": segment.no_speech_prob,
                    "words": [],
                }

                # Add word-level timestamps if available
                if hasattr(segment, "words") and segment.words:
                    segment_dict["words"] = [
                        {
                            "start": word.start,
                            "end": word.end,
                            "word": word.word,
                            "probability": word.probability,
                        }
                        for word in segment.words
                    ]

                segments_list.append(segment_dict)

            # Format result to match openai-whisper structure
            result = {
                "segments": segments_list,
                "language": info.language,
                "language_probability": info.language_probability,
                "duration": info.duration,
                "text": " ".join([seg["text"] for seg in segments_list]),
            }

            logger.info(f"Transcription completed: {len(segments_list)} segments")

            return result

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise

    def format_transcript_with_timestamps(self, result: Dict) -> List[Dict]:
        """
        Format transcription result into structured list.

        Args:
            result: Whisper transcription result

        Returns:
            List of dictionaries with start, end, text, confidence
        """
        formatted = []

        for segment in result.get("segments", []):
            formatted.append(
                {
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"].strip(),
                    "confidence": segment.get("avg_logprob", 0.0),
                }
            )

        return formatted

    def get_text_at_timestamp(
        self, transcript: List[Dict], timestamp: float, window: float = 5.0
    ) -> str:
        """
        Get text around a specific timestamp.

        Args:
            transcript: Formatted transcript
            timestamp: Target timestamp in seconds
            window: Time window in seconds (±window)

        Returns:
            Text within the time window
        """
        texts = []

        for entry in transcript:
            if entry["start"] >= (timestamp - window) and entry["end"] <= (
                timestamp + window
            ):
                texts.append(entry["text"])

        return " ".join(texts)

    def get_full_text(self, transcript: List[Dict]) -> str:
        """
        Get full transcript as plain text.

        Args:
            transcript: Formatted transcript

        Returns:
            Full text
        """
        return " ".join([entry["text"] for entry in transcript])

    def find_sentence_boundaries(
        self, transcript: List[Dict], start_time: float, end_time: float
    ) -> tuple[float, float]:
        """
        Adjust time boundaries to not cut sentences mid-word.

        Args:
            transcript: Formatted transcript
            start_time: Desired start time
            end_time: Desired end time

        Returns:
            Adjusted (start_time, end_time) tuple
        """
        # Find closest segment boundaries
        adjusted_start = start_time
        adjusted_end = end_time

        for entry in transcript:
            # Find segment that contains or is closest to start_time
            if entry["start"] <= start_time <= entry["end"]:
                adjusted_start = entry["start"]
            elif entry["start"] > start_time:
                adjusted_start = entry["start"]
                break

        for entry in reversed(transcript):
            # Find segment that contains or is closest to end_time
            if entry["start"] <= end_time <= entry["end"]:
                adjusted_end = entry["end"]
                break
            elif entry["end"] < end_time:
                adjusted_end = entry["end"]

        return adjusted_start, adjusted_end

    def extract_segment_transcript(
        self, transcript: List[Dict], start_time: float, end_time: float,
        convert_to_relative: bool = True
    ) -> List[Dict]:
        """
        Extract transcript segment within time range.

        Args:
            transcript: Full transcript
            start_time: Start time in seconds (absolute, from original video)
            end_time: End time in seconds (absolute, from original video)
            convert_to_relative: If True, converts timestamps to be relative to start_time (default: True)

        Returns:
            List of transcript entries within range, with timestamps relative to segment start
        """
        segment = []
        segment_duration = end_time - start_time

        for entry in transcript:
            if entry["start"] >= start_time and entry["end"] <= end_time:
                # Fully contained in segment
                if convert_to_relative:
                    segment.append({
                        "start": entry["start"] - start_time,
                        "end": entry["end"] - start_time,
                        "text": entry["text"],
                        "confidence": entry.get("confidence", 0.0),
                    })
                else:
                    segment.append(entry)
            elif entry["start"] < end_time and entry["end"] > start_time:
                # Partial overlap - clamp to segment boundaries
                if convert_to_relative:
                    rel_start = max(0.0, entry["start"] - start_time)
                    rel_end = min(segment_duration, entry["end"] - start_time)
                    segment.append({
                        "start": rel_start,
                        "end": rel_end,
                        "text": entry["text"],
                        "confidence": entry.get("confidence", 0.0),
                    })
                else:
                    segment.append(entry)

        logger.debug(f"Extracted {len(segment)} transcript entries for segment {start_time:.2f}s-{end_time:.2f}s (relative={convert_to_relative})")
        return segment

    def get_word_level_transcript(self, result: Dict) -> List[Dict]:
        """
        Extract word-level timestamps from Whisper result.

        Args:
            result: Whisper transcription result with word timestamps

        Returns:
            List of dictionaries with {start, end, word} for each word
        """
        words = []

        for segment in result.get("segments", []):
            if "words" in segment and segment["words"]:
                for word_data in segment["words"]:
                    words.append(
                        {
                            "start": word_data["start"],
                            "end": word_data["end"],
                            "word": word_data["word"].strip(),
                        }
                    )

        return words
