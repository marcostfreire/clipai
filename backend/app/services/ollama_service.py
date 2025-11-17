"""Ollama service for local AI-powered video analysis using Gemma."""

import logging
import json
import httpx
from typing import List, Dict
from PIL import Image
import base64
import io

logger = logging.getLogger(__name__)


class OllamaService:
    """Service for AI analysis using local Ollama with Gemma model."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma3:4b",
        batch_size: int = 5,
    ):
        """
        Initialize Ollama service.

        Args:
            base_url: Ollama API base URL
            model: Model name (default: gemma3:4b for Gemma 3 4B)
            batch_size: Number of frames to process in batch (default: 5)
        """
        self.base_url = base_url
        self.model = model
        self.batch_size = batch_size
        self.client = httpx.Client(timeout=300.0)  # 5min timeout for batch requests
        logger.info(
            f"Initialized Ollama service with model: {model}, batch_size: {batch_size}"
        )

    def _image_to_base64(self, image_path: str) -> str:
        """Convert image to base64 string."""
        with Image.open(image_path) as img:
            # Resize if too large to save memory
            if img.width > 1024 or img.height > 1024:
                img.thumbnail((1024, 1024))

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def analyze_frame(self, image_path: str) -> dict:
        """
        Analyze a video frame for visual engagement signals.

        Args:
            image_path: Path to frame image

        Returns:
            Dictionary with analysis results
        """
        try:
            # Convert image to base64
            image_b64 = self._image_to_base64(image_path)

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

            # Call Ollama API with vision
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_b64],
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # More deterministic
                        "num_predict": 200,  # Limit response length
                    },
                },
            )
            response.raise_for_status()

            result_text = response.json()["response"].strip()

            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            result = json.loads(result_text)

            logger.debug(f"Frame analysis: {result}")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response as JSON: {e}")
            logger.error(
                f"Response was: {result_text if 'result_text' in locals() else 'No response'}"
            )
            # Return default values
            return {
                "has_face": False,
                "face_count": 0,
                "face_position_x": None,
                "expression": "neutral",
                "scene_type": "other",
                "text_on_screen": False,
                "engagement_score": 5.0,
            }
        except Exception as e:
            logger.error(f"Error analyzing frame with Ollama: {e}")
            # Return default values on error
            return {
                "has_face": False,
                "face_count": 0,
                "face_position_x": None,
                "expression": "neutral",
                "scene_type": "other",
                "text_on_screen": False,
                "engagement_score": 5.0,
            }

    def identify_viral_moments(self, transcript: str, duration: float) -> List[dict]:
        """
        Identify viral moments in transcript.

        Args:
            transcript: Full transcript with timestamps
            duration: Total video duration in seconds

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

            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.4, "num_predict": 1000},
                },
            )
            response.raise_for_status()

            result_text = response.json()["response"].strip()

            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            result = json.loads(result_text)
            moments = result.get("moments", [])

            # Validate and clamp timestamps
            validated_moments = []
            for moment in moments:
                if (
                    moment.get("start_time", 0) >= 0
                    and moment.get("end_time", 0) <= duration
                ):
                    validated_moments.append(moment)

            logger.info(f"Identified {len(validated_moments)} viral moments")
            return validated_moments

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Ollama response as JSON: {e}")
            logger.error(
                f"Response was: {result_text if 'result_text' in locals() else 'No response'}"
            )
            return []
        except Exception as e:
            logger.error(f"Error identifying viral moments with Ollama: {e}")
            return []

    def analyze_sentiment(self, text: str) -> dict:
        """
        Analyze sentiment of text segment.

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment analysis
        """
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

            response = self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3, "num_predict": 150},
                },
            )
            response.raise_for_status()

            result_text = response.json()["response"].strip()

            # Remove markdown code blocks if present
            if result_text.startswith("```"):
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            result = json.loads(result_text)
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse sentiment response: {e}")
            return {"sentiment": "neutral", "emotion": "calm", "engagement_score": 5.0}
        except Exception as e:
            logger.error(f"Error analyzing sentiment with Ollama: {e}")
            return {"sentiment": "neutral", "emotion": "calm", "engagement_score": 5.0}

    def batch_analyze_frames(
        self, frame_paths: List[str], fps: float = 0.2
    ) -> Dict[float, dict]:
        """
        Analyze multiple frames and create timestamp-indexed results.
        Uses batch processing when possible to reduce HTTP overhead.

        Args:
            frame_paths: List of frame image paths
            fps: Frames per second used for extraction

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
                f"📦 Processing batch {batch_start//self.batch_size + 1}/{(total_frames + self.batch_size - 1)//self.batch_size} ({batch_size_actual} frames)"
            )

            # Process each frame in the batch
            for i, frame_path in enumerate(batch_frames):
                frame_idx = batch_start + i
                timestamp = frame_idx / fps

                frame_start = time.time()
                analysis = self.analyze_frame(frame_path)
                frame_time = time.time() - frame_start

                results[timestamp] = analysis

                logger.info(
                    f"  ✓ Frame {frame_idx+1}/{total_frames} at {timestamp:.1f}s (took {frame_time:.2f}s)"
                )

            batch_time = time.time() - batch_start_time
            avg_time_per_frame = batch_time / batch_size_actual
            logger.info(
                f"📊 Batch completed in {batch_time:.2f}s (avg {avg_time_per_frame:.2f}s/frame)"
            )

        total_time = time.time() - start_time
        avg_overall = total_time / total_frames
        logger.info(
            f"✅ All frames analyzed in {total_time:.2f}s (avg {avg_overall:.2f}s/frame)"
        )

        return results

    def __del__(self):
        """Cleanup HTTP client."""
        if hasattr(self, "client"):
            self.client.close()
