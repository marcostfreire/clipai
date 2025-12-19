"""Gemini service for AI-powered video analysis using Google Genai."""

import logging
import json
import base64
import io
import os
from typing import List, Dict, Optional
from PIL import Image

logger = logging.getLogger(__name__)

# Lazy import for google.genai
_genai_client = None


def _get_client(api_key: str):
    """Get or create Google Genai client."""
    global _genai_client
    if _genai_client is None:
        from google import genai
        _genai_client = genai.Client(api_key=api_key)
    return _genai_client


class GeminiService:
    """Service for AI analysis using Google Gemini models."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_default: str = "gemini-2.5-flash-lite",
        model_strict: str = "gemini-2.5-flash",
        batch_size: int = 2,
        timeout: int = 120,
        max_retries: int = 3,
    ):
        """
        Initialize Gemini service.

        Args:
            api_key: Google API key (falls back to GOOGLE_API_KEY env var)
            model_default: Default model for most operations (gemini-2.5-flash-lite)
            model_strict: Model for complex reasoning (gemini-2.5-flash)
            batch_size: Number of frames to process in batch (default: 2)
            timeout: Request timeout in seconds (default: 120)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable or api_key parameter required")
        
        self.model_default = model_default
        self.model_strict = model_strict
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize client
        self._client = _get_client(self.api_key)
        
        logger.info(
            f"Initialized Gemini service with models: default={model_default}, strict={model_strict}, batch_size={batch_size}"
        )

    def _load_image_bytes(self, image_path: str) -> bytes:
        """Load and resize image, return as bytes."""
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize if too large to save memory/bandwidth
            if img.width > 1024 or img.height > 1024:
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return buffer.getvalue()

    def _call_with_retry(self, model_name: str, contents: list, config: dict = None) -> str:
        """Call Gemini API with retry logic."""
        import time
        from google import genai
        from google.genai import types
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Build generation config
                gen_config = None
                if config:
                    gen_config = types.GenerateContentConfig(
                        temperature=config.get("temperature", 0.3),
                        max_output_tokens=config.get("max_output_tokens", 500),
                    )
                
                response = self._client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=gen_config,
                )
                return response.text.strip()
            except Exception as e:
                last_error = e
                wait_time = (attempt + 1) * 2  # Exponential backoff: 2, 4, 6 seconds
                logger.warning(f"Gemini API call failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(wait_time)
        
        raise last_error

    def _parse_json_response(self, response_text: str, default: dict) -> dict:
        """Parse JSON from response, handling markdown code blocks."""
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line (```)
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response was: {response_text[:500]}")
            return default

    def analyze_frame(self, image_path: str, use_strict: bool = False) -> dict:
        """
        Analyze a video frame for visual engagement signals.

        Args:
            image_path: Path to frame image
            use_strict: Use gemini-2.5-flash instead of flash-lite

        Returns:
            Dictionary with analysis results
        """
        from google.genai import types
        
        default_result = {
            "has_face": False,
            "face_count": 0,
            "face_position_x": None,
            "expression": "neutral",
            "scene_type": "other",
            "text_on_screen": False,
            "engagement_score": 5.0,
        }
        
        try:
            # Load and prepare image
            image_bytes = self._load_image_bytes(image_path)
            
            prompt = """Analyze this video frame and respond ONLY with valid JSON (no markdown, no extra text):
{
  "has_face": true/false,
  "face_count": 0-10 (number of faces detected),
  "face_position_x": 0-100 (horizontal position percentage from left, or null),
  "expression": "neutral" or "excited" or "serious" or "laughing",
  "scene_type": "talking_head" or "presentation" or "action" or "other",
  "text_on_screen": true/false,
  "engagement_score": 0-10 (number)
}

Rate engagement based on:
- Face presence and expression (higher for excited/laughing)
- Dynamic content (higher for action)
- Text overlays (slightly higher)
- Composition quality

Important instructions:
- Count the number of faces visible in the frame and set face_count accordingly
- If face_count is exactly 1, estimate the horizontal position of the face center as a percentage:
  * 0-20% = face is on far left edge
  * 20-40% = face is on left side
  * 40-60% = face is centered
  * 60-80% = face is on right side
  * 80-100% = face is on far right edge
- If face_count is 0 or more than 1, set face_position_x to null
- Be precise with the percentage estimate

Respond with ONLY the JSON object, nothing else."""

            # Select model
            model_name = self.model_strict if use_strict else self.model_default
            
            # Create image part
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            
            # Build contents
            contents = [prompt, image_part]
            
            config = {
                "temperature": 0.3,
                "max_output_tokens": 200,
            }
            
            response_text = self._call_with_retry(model_name, contents, config)
            
            result = self._parse_json_response(response_text, default_result)
            logger.debug(f"Frame analysis: {result}")
            return result

        except Exception as e:
            logger.error(f"Error analyzing frame with Gemini: {e}")
            return default_result

    def identify_viral_moments(
        self, transcript: str, duration: float, use_strict: bool = False
    ) -> List[dict]:
        """
        Identify viral moments in transcript.

        Args:
            transcript: Full transcript text
            duration: Total video duration in seconds
            use_strict: Use gemini-2.5-flash instead of flash-lite

        Returns:
            List of viral moment dictionaries
        """
        try:
            prompt = f"""Analyze this video transcript and identify the TOP 5 most viral/engaging moments.

Video duration: {duration} seconds

Transcript:
{transcript}

Respond ONLY with valid JSON (no markdown, no extra text):
{{
  "moments": [
    {{
      "start_time": <float seconds>,
      "end_time": <float seconds>,
      "reason": "<why this is viral>",
      "keywords": ["<key>", "<words>"],
      "virality_score": <0-10 number>,
      "hook_type": "question" or "revelation" or "humor" or "insight" or "story"
    }}
  ]
}}

Look for:
- Questions that create curiosity
- Surprising revelations or facts
- Humorous moments
- Valuable insights/tips
- Compelling stories
- Emotional peaks
- Controversial statements

Each moment should be 30-60 seconds. Ensure start_time and end_time are within 0-{duration} seconds.
Respond with ONLY the JSON object, nothing else."""

            # Select model
            model_name = self.model_strict if use_strict else self.model_default
            
            config = {
                "temperature": 0.4,
                "max_output_tokens": 1000,
            }
            
            response_text = self._call_with_retry(model_name, [prompt], config)
            
            result = self._parse_json_response(response_text, {"moments": []})
            moments = result.get("moments", [])

            # Validate and clamp timestamps
            validated_moments = []
            for moment in moments:
                start = moment.get("start_time", 0)
                end = moment.get("end_time", 0)
                if start >= 0 and end <= duration and start < end:
                    validated_moments.append(moment)

            logger.info(f"Identified {len(validated_moments)} viral moments")
            return validated_moments

        except Exception as e:
            logger.error(f"Error identifying viral moments with Gemini: {e}")
            return []

    def analyze_sentiment(self, text: str, use_strict: bool = False) -> dict:
        """
        Analyze sentiment of text segment.

        Args:
            text: Text to analyze
            use_strict: Use gemini-2.5-flash instead of flash-lite

        Returns:
            Dictionary with sentiment analysis
        """
        default_result = {
            "sentiment": "neutral",
            "emotion": "calm",
            "engagement_score": 5.0,
        }
        
        try:
            prompt = f"""Analyze the sentiment and engagement level of this text.

Text:
{text}

Respond ONLY with valid JSON (no markdown, no extra text):
{{
  "sentiment": "positive" or "negative" or "neutral",
  "emotion": "excited" or "calm" or "serious" or "humorous",
  "engagement_score": <0-10 number>
}}

Respond with ONLY the JSON object, nothing else."""

            # Select model
            model_name = self.model_strict if use_strict else self.model_default
            
            config = {
                "temperature": 0.3,
                "max_output_tokens": 150,
            }
            
            response_text = self._call_with_retry(model_name, [prompt], config)
            
            return self._parse_json_response(response_text, default_result)

        except Exception as e:
            logger.error(f"Error analyzing sentiment with Gemini: {e}")
            return default_result

    def batch_analyze_frames(
        self, frame_paths: List[str], fps: float = 0.1, use_strict: bool = False
    ) -> Dict[float, dict]:
        """
        Analyze multiple frames and create timestamp-indexed results.

        Args:
            frame_paths: List of frame image paths
            fps: Frames per second used for extraction
            use_strict: Use gemini-2.5-flash instead of flash-lite

        Returns:
            Dictionary mapping timestamp to analysis
        """
        import time

        results = {}
        total_frames = len(frame_paths)

        logger.info(
            f"🚀 Starting batch analysis of {total_frames} frames (batch_size={self.batch_size})"
        )
        start_time = time.time()

        # Process frames in batches
        for batch_start in range(0, total_frames, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_frames)
            batch_frames = frame_paths[batch_start:batch_end]
            batch_size_actual = len(batch_frames)

            batch_start_time = time.time()
            logger.info(
                f"📦 Processing batch {batch_start // self.batch_size + 1}/{(total_frames + self.batch_size - 1) // self.batch_size} ({batch_size_actual} frames)"
            )

            # Process each frame in the batch
            for i, frame_path in enumerate(batch_frames):
                frame_idx = batch_start + i
                timestamp = frame_idx / fps

                frame_start = time.time()
                analysis = self.analyze_frame(frame_path, use_strict=use_strict)
                frame_time = time.time() - frame_start

                results[timestamp] = analysis

                logger.info(
                    f"  ✓ Frame {frame_idx + 1}/{total_frames} at {timestamp:.1f}s (took {frame_time:.2f}s)"
                )

            batch_time = time.time() - batch_start_time
            avg_time_per_frame = batch_time / batch_size_actual
            logger.info(
                f"📊 Batch completed in {batch_time:.2f}s (avg {avg_time_per_frame:.2f}s/frame)"
            )

        total_time = time.time() - start_time
        avg_overall = total_time / total_frames if total_frames > 0 else 0
        logger.info(
            f"✅ All frames analyzed in {total_time:.2f}s (avg {avg_overall:.2f}s/frame)"
        )

        return results
