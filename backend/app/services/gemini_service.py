"""Gemini service for AI-powered video analysis using Google Genai."""

import logging
import json
import base64
import io
import os
from typing import List, Dict, Optional, Tuple
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


def _compute_image_hash(image_path: str) -> Optional[str]:
    """
    Compute perceptual hash of an image for deduplication.
    
    Uses average hash (aHash) which is fast and good for detecting similar frames.
    Falls back to difference hash if imagehash not available.
    """
    try:
        import imagehash
        with Image.open(image_path) as img:
            # Use perceptual hash - robust to minor changes
            phash = imagehash.phash(img, hash_size=16)
            return str(phash)
    except ImportError:
        # Fallback: simple average hash implementation
        logger.warning("imagehash not installed, using fallback hash")
        try:
            with Image.open(image_path) as img:
                img = img.convert('L').resize((16, 16), Image.Resampling.LANCZOS)
                pixels = list(img.getdata())
                avg = sum(pixels) / len(pixels)
                bits = ''.join('1' if p > avg else '0' for p in pixels)
                return hex(int(bits, 2))
        except Exception as e:
            logger.error(f"Failed to compute fallback hash: {e}")
            return None
    except Exception as e:
        logger.error(f"Failed to compute image hash: {e}")
        return None


def _hash_distance(hash1: str, hash2: str) -> int:
    """
    Calculate Hamming distance between two hashes.
    Lower distance = more similar images.
    """
    try:
        import imagehash
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
    except ImportError:
        # Fallback: simple XOR distance
        try:
            i1 = int(hash1, 16)
            i2 = int(hash2, 16)
            xor = i1 ^ i2
            return bin(xor).count('1')
        except:
            return 999  # Force as different if comparison fails
    except:
        return 999


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
                # Build generation config with JSON response format
                gen_config = None
                if config:
                    gen_config = types.GenerateContentConfig(
                        temperature=config.get("temperature", 0.3),
                        max_output_tokens=config.get("max_output_tokens", 1000),
                        response_mime_type="application/json",  # Force pure JSON output
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
        """Parse JSON from response, handling markdown code blocks and truncated responses."""
        text = response_text.strip()
        
        # Remove markdown code blocks if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```)
            lines = lines[1:]
            # Remove last line (```) if present
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        
        # Try to parse as-is first
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Try to repair truncated JSON
            repaired = self._try_repair_json(text, default)
            if repaired != default:
                logger.warning(f"Repaired truncated JSON response")
                return repaired
            
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Response was: {response_text[:200]}...")
            return default
    
    def _try_repair_json(self, text: str, default: dict) -> dict:
        """Attempt to repair truncated JSON responses."""
        import re
        
        # If it looks like it was truncated mid-response, try to extract what we can
        text = text.strip()
        
        # For frame analysis - try to extract individual fields
        if '"has_face"' in text:
            result = default.copy()
            
            # Extract has_face
            match = re.search(r'"has_face"\s*:\s*(true|false)', text, re.IGNORECASE)
            if match:
                result["has_face"] = match.group(1).lower() == "true"
            
            # Extract face_count
            match = re.search(r'"face_count"\s*:\s*(\d+)', text)
            if match:
                result["face_count"] = int(match.group(1))
            
            # Extract face_position_x
            match = re.search(r'"face_position_x"\s*:\s*(\d+(?:\.\d+)?|null)', text)
            if match:
                val = match.group(1)
                result["face_position_x"] = None if val == "null" else float(val)
            
            # Extract expression
            match = re.search(r'"expression"\s*:\s*"(\w+)"', text)
            if match:
                result["expression"] = match.group(1)
            
            # Extract scene_type
            match = re.search(r'"scene_type"\s*:\s*"([\w_]+)"', text)
            if match:
                result["scene_type"] = match.group(1)
            
            # Extract engagement_score
            match = re.search(r'"engagement_score"\s*:\s*(\d+(?:\.\d+)?)', text)
            if match:
                result["engagement_score"] = float(match.group(1))
            
            # Only return if we extracted something useful
            if result.get("has_face") is not None or result.get("face_count", 0) > 0:
                return result
        
        # For viral moments - try to extract the moments array
        if '"moments"' in text:
            # Try to find complete moment objects
            moments = []
            # Find all complete moment objects using regex
            pattern = r'\{[^{}]*"start_time"\s*:\s*([\d.]+)[^{}]*"end_time"\s*:\s*([\d.]+)[^{}]*"virality_score"\s*:\s*([\d.]+)[^{}]*\}'
            for match in re.finditer(pattern, text, re.DOTALL):
                try:
                    moments.append({
                        "start_time": float(match.group(1)),
                        "end_time": float(match.group(2)),
                        "virality_score": float(match.group(3)),
                        "reason": "extracted from truncated response",
                        "keywords": [],
                        "hook_type": "insight"
                    })
                except:
                    pass
            
            if moments:
                return {"moments": moments}
        
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

CRITICAL INSTRUCTIONS FOR FACE DETECTION:
1. Count ALL visible human faces in the frame
2. For face_position_x, identify the MAIN SPEAKER or PRIMARY SUBJECT:
   - In TV news: focus on the reporter/anchor speaking (usually larger face)
   - In split-screen layouts: focus on the person actually speaking
   - In picture-in-picture: focus on the main content, not the small inset
3. Estimate face_position_x as percentage from LEFT edge (0%) to RIGHT edge (100%):
   * 0-15% = face at far left edge
   * 15-35% = face on left side  
   * 35-65% = face is centered
   * 65-85% = face on right side
   * 85-100% = face at far right edge
4. For split-screen with 2 people: set face_position_x to the PRIMARY speaker's position
5. Only set face_position_x to null if there are NO faces

BE VERY PRECISE with the percentage - this determines how the video will be cropped.

Respond with ONLY the JSON object, nothing else."""

            # Select model
            model_name = self.model_strict if use_strict else self.model_default
            
            # Create image part
            image_part = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            
            # Build contents
            contents = [prompt, image_part]
            
            config = {
                "temperature": 0.2,  # Lower temperature for more consistent detection
                "max_output_tokens": 500,  # Increased from 200 to prevent truncation
            }
            
            response_text = self._call_with_retry(model_name, contents, config)
            
            result = self._parse_json_response(response_text, default_result)
            logger.info(f"🔍 Frame analysis: faces={result.get('face_count')}, pos={result.get('face_position_x')}%, scene={result.get('scene_type')}")
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

            # Select model - use strict model for better reasoning on viral detection
            model_name = self.model_strict  # Always use gemini-2.5-flash for viral detection
            
            config = {
                "temperature": 0.4,
                "max_output_tokens": 4000,  # Increased from 1000 - need space for 5 detailed moments
            }
            
            response_text = self._call_with_retry(model_name, [prompt], config)
            
            result = self._parse_json_response(response_text, {"moments": []})
            moments = result.get("moments", [])

            logger.info(f"📺 Gemini returned {len(moments)} raw moments")
            for i, m in enumerate(moments):
                logger.info(f"  [{i+1}] Score: {m.get('virality_score', 0)}, Time: {m.get('start_time', 0):.1f}s-{m.get('end_time', 0):.1f}s, Type: {m.get('hook_type', 'N/A')}")

            # Validate and clamp timestamps
            validated_moments = []
            for moment in moments:
                start = moment.get("start_time", 0)
                end = moment.get("end_time", 0)
                if start >= 0 and end <= duration and start < end:
                    validated_moments.append(moment)
                else:
                    logger.warning(f"⚠️ Invalid moment timestamps: {start:.1f}s-{end:.1f}s (duration: {duration:.1f}s)")

            logger.info(f"✅ Validated {len(validated_moments)} viral moments")
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
        self, frame_paths: List[str], fps: float = 0.1, use_strict: bool = False,
        dedup_threshold: int = 12
    ) -> Dict[float, dict]:
        """
        Analyze multiple frames and create timestamp-indexed results.
        Uses perceptual hashing to skip similar/duplicate frames.

        Args:
            frame_paths: List of frame image paths
            fps: Frames per second used for extraction
            use_strict: Use gemini-2.5-flash instead of flash-lite
            dedup_threshold: Max hash distance to consider frames as duplicates (0-64, lower=stricter)
                            Default 12 is good for detecting scene changes while skipping static frames.

        Returns:
            Dictionary mapping timestamp to analysis
        """
        import time

        results = {}
        total_frames = len(frame_paths)
        
        # Deduplication tracking
        prev_hash: Optional[str] = None
        prev_analysis: Optional[dict] = None
        api_calls = 0
        skipped_frames = 0

        logger.info(
            f"🚀 Starting batch analysis of {total_frames} frames (dedup_threshold={dedup_threshold})"
        )
        start_time = time.time()

        # Process frames in batches
        for batch_start in range(0, total_frames, self.batch_size):
            batch_end = min(batch_start + self.batch_size, total_frames)
            batch_frames = frame_paths[batch_start:batch_end]
            batch_size_actual = len(batch_frames)

            batch_start_time = time.time()
            batch_api_calls = 0
            batch_skipped = 0
            
            logger.info(
                f"📦 Processing batch {batch_start // self.batch_size + 1}/{(total_frames + self.batch_size - 1) // self.batch_size} ({batch_size_actual} frames)"
            )

            # Process each frame in the batch
            for i, frame_path in enumerate(batch_frames):
                frame_idx = batch_start + i
                timestamp = frame_idx / fps

                # Compute hash for deduplication
                current_hash = _compute_image_hash(frame_path)
                
                # Check if frame is similar to previous
                is_duplicate = False
                if prev_hash and current_hash:
                    distance = _hash_distance(current_hash, prev_hash)
                    if distance <= dedup_threshold:
                        is_duplicate = True
                        skipped_frames += 1
                        batch_skipped += 1
                        
                        # Reuse previous analysis
                        if prev_analysis:
                            results[timestamp] = prev_analysis.copy()
                            logger.debug(
                                f"  ⏭️ Frame {frame_idx + 1}/{total_frames} at {timestamp:.1f}s - SKIPPED (hash distance: {distance})"
                            )
                
                if not is_duplicate:
                    # Actually call the API
                    frame_start = time.time()
                    analysis = self.analyze_frame(frame_path, use_strict=use_strict)
                    frame_time = time.time() - frame_start

                    results[timestamp] = analysis
                    prev_analysis = analysis
                    api_calls += 1
                    batch_api_calls += 1

                    logger.info(
                        f"  ✓ Frame {frame_idx + 1}/{total_frames} at {timestamp:.1f}s (took {frame_time:.2f}s)"
                    )
                
                # Update previous hash
                prev_hash = current_hash

            batch_time = time.time() - batch_start_time
            avg_time_per_frame = batch_time / batch_size_actual
            logger.info(
                f"📊 Batch completed in {batch_time:.2f}s - API calls: {batch_api_calls}, Skipped: {batch_skipped}"
            )

        total_time = time.time() - start_time
        dedup_rate = (skipped_frames / total_frames * 100) if total_frames > 0 else 0
        
        logger.info(
            f"✅ Analysis complete in {total_time:.2f}s"
        )
        logger.info(
            f"📈 Dedup stats: {api_calls} API calls, {skipped_frames} frames skipped ({dedup_rate:.1f}% savings)"
        )

        return results
