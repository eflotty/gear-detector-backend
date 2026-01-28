"""
Vision-based gear identification using Claude Vision API
"""
from anthropic import AsyncAnthropic
import base64
import logging
from typing import Dict, Optional
import json
from PIL import Image
import io

from src.config import settings

logger = logging.getLogger(__name__)


class VisionService:
    """Identify guitar gear from photos using Claude Vision"""

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self.model = settings.claude_model

    async def identify_gear_from_image(
        self,
        image_data: bytes,
        gear_type: Optional[str] = None,
        context: Optional[str] = None
    ) -> Dict:
        """
        Analyze image with Claude Vision to identify guitar gear

        Args:
            image_data: Raw image bytes (JPEG/PNG)
            gear_type: Optional hint (guitar, amp, pedal)
            context: Optional context (e.g., 'music video screenshot')

        Returns:
            GearResult-compatible dict with guitars, amps, pedals, confidence
        """
        if not self.client:
            logger.error("Claude API not configured - cannot analyze image")
            raise ValueError("Claude API key not configured. Please set ANTHROPIC_API_KEY in environment variables.")

        prompt = self._build_vision_prompt(gear_type, context)

        logger.info(f"🔍 Analyzing image with Claude Vision (type hint: {gear_type}, context: {context})")

        try:
            # Optimize image size to reduce costs
            image_data = self._optimize_image(image_data)
            logger.info(f"📦 Optimized image size: {len(image_data)} bytes")

            # Detect media type from image data
            media_type = self._detect_media_type(image_data)

            # Call Claude Vision API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.2,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.b64encode(image_data).decode()
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }]
            )

            # Parse JSON response
            gear_data = self._parse_vision_response(response.content[0].text)

            logger.info(f"✅ Vision analysis complete - confidence: {gear_data.get('confidence_score', 0):.1f}%")

            return gear_data

        except Exception as e:
            logger.error(f"Vision API error: {e}", exc_info=True)
            raise

    def _optimize_image(self, image_data: bytes, max_size: int = 1536) -> bytes:
        """
        Optimize image for API submission
        - Resize to max dimension while preserving aspect ratio
        - Convert to JPEG with quality optimization
        - Reduce file size to minimize costs

        Args:
            image_data: Original image bytes
            max_size: Maximum width/height in pixels (default: 1536)

        Returns:
            Optimized image bytes
        """
        try:
            # Open image
            img = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary (for PNG with transparency, etc.)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background

            # Resize if needed
            width, height = img.size
            if width > max_size or height > max_size:
                # Calculate new dimensions
                if width > height:
                    new_width = max_size
                    new_height = int(height * (max_size / width))
                else:
                    new_height = max_size
                    new_width = int(width * (max_size / height))

                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                logger.info(f"🔧 Resized image from {width}x{height} to {new_width}x{new_height}")

            # Save as JPEG with optimization
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            optimized_data = output.getvalue()

            # Log compression ratio
            original_size = len(image_data)
            optimized_size = len(optimized_data)
            ratio = (1 - optimized_size / original_size) * 100
            logger.info(f"📉 Compressed image: {original_size} → {optimized_size} bytes ({ratio:.1f}% reduction)")

            return optimized_data

        except Exception as e:
            logger.warning(f"Image optimization failed: {e}. Using original image.")
            return image_data

    def _detect_media_type(self, image_data: bytes) -> str:
        """Detect image media type from magic bytes"""
        if image_data.startswith(b'\xff\xd8\xff'):
            return "image/jpeg"
        elif image_data.startswith(b'\x89PNG'):
            return "image/png"
        elif image_data.startswith(b'GIF'):
            return "image/gif"
        elif image_data.startswith(b'RIFF') and b'WEBP' in image_data[:12]:
            return "image/webp"
        else:
            # Default to JPEG
            return "image/jpeg"

    def _parse_year(self, year_str: str) -> Optional[int]:
        """
        Parse year from string, handling ranges like "1958-1960" or "1965 (reissue)"

        Args:
            year_str: Year string from Claude Vision

        Returns:
            First valid year as integer, or None if parsing fails
        """
        import re

        try:
            # Extract first 4-digit number
            match = re.search(r'\b(19\d{2}|20\d{2})\b', year_str)
            if match:
                return int(match.group(1))

            # Try to parse as plain integer
            return int(year_str)
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse year: {year_str}")
            return None

    def _build_vision_prompt(self, gear_type: Optional[str], context: Optional[str]) -> str:
        """Build prompt for Claude Vision"""
        gear_hint = f"\nUser hint: Looking for {gear_type}" if gear_type else ""
        context_hint = f"\nContext: {context}" if context else ""

        return f"""You are an expert guitar gear identification system analyzing a photo.

Identify all visible guitar gear: guitars, amps, pedals.

For each item, determine:
- Make and model (e.g., "Fender Stratocaster", "Marshall JCM800")
- Year if identifiable (single integer year only, e.g., 1965. For ranges, use the earliest year. Include era info in notes if needed.)
- Key visual cues used for identification

Confidence levels:
- 90-100% (Confirmed): Clear logo, distinctive model features visible
- 70-89% (Likely): Strong visual match, characteristic features
- 50-69% (Possible): General shape/style match, some uncertainty
- <50% (Uncertain): Speculative based on limited info
{gear_hint}{context_hint}

Return ONLY valid JSON:
{{
  "guitars": [
    {{
      "make": "Fender",
      "model": "Stratocaster",
      "year": 1965,
      "notes": "Identified by: three-tone sunburst, rosewood fretboard, vintage tremolo",
      "confidence": 92.0,
      "sources": ["claude_vision"]
    }}
  ],
  "amps": [],
  "pedals": [],
  "signal_chain": [
    {{"type": "guitar", "item": "Fender Stratocaster"}},
    {{"type": "amp", "item": "Fender Twin Reverb"}}
  ],
  "context": "Photo analysis identified X items with Y visual clarity...",
  "confidence_score": 85.0,
  "reasoning": {{
    "visual_quality": "excellent",
    "identification_basis": "Logos, model features, shape/color",
    "uncertainty_factors": "None"
  }}
}}"""

    def _parse_vision_response(self, response_text: str) -> Dict:
        """
        Parse Claude Vision response into GearResult format

        Args:
            response_text: Raw text from Claude API

        Returns:
            Structured gear data dict
        """
        try:
            # Extract JSON from response (may be wrapped in markdown code blocks)
            json_str = response_text.strip()

            # Remove markdown code blocks if present
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            elif json_str.startswith("```"):
                json_str = json_str[3:]

            if json_str.endswith("```"):
                json_str = json_str[:-3]

            json_str = json_str.strip()

            # Parse JSON
            gear_data = json.loads(json_str)

            # Validate required fields
            if "guitars" not in gear_data:
                gear_data["guitars"] = []
            if "amps" not in gear_data:
                gear_data["amps"] = []
            if "pedals" not in gear_data:
                gear_data["pedals"] = []
            if "signal_chain" not in gear_data:
                gear_data["signal_chain"] = []
            if "confidence_score" not in gear_data:
                gear_data["confidence_score"] = 50.0
            if "context" not in gear_data:
                gear_data["context"] = "Photo analysis completed"

            # Fix year fields - convert strings to integers
            for guitar in gear_data.get("guitars", []):
                if "year" in guitar and isinstance(guitar["year"], str):
                    guitar["year"] = self._parse_year(guitar["year"])

            return gear_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse vision response as JSON: {e}")
            logger.error(f"Response text: {response_text[:500]}")

            # Return minimal valid structure
            return {
                "guitars": [],
                "amps": [],
                "pedals": [],
                "signal_chain": [],
                "context": f"Error parsing vision response: {str(e)}",
                "confidence_score": 0.0,
                "reasoning": {
                    "visual_quality": "unknown",
                    "identification_basis": "parse_error",
                    "uncertainty_factors": str(e)
                }
            }
