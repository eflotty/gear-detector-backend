"""
Claude AI service for synthesizing gear data
"""
from anthropic import AsyncAnthropic
from typing import List, Dict
import json
import logging

from src.scrapers.base_scraper import ScraperResult
from src.config import settings

logger = logging.getLogger(__name__)


class ClaudeService:
    """
    Interfaces with Claude API to synthesize gear data
    """

    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self.model = settings.claude_model
        self.max_tokens = settings.claude_max_tokens

    async def synthesize_gear_data(
        self,
        artist: str,
        song: str,
        scraper_results: List[ScraperResult]
    ) -> Dict:
        """
        Use Claude to synthesize raw data into structured gear information

        Args:
            artist: Artist name
            song: Song title
            scraper_results: List of results from various scrapers

        Returns:
            Structured gear data with confidence scores
        """
        if not self.client:
            logger.error("Claude API not configured")
            return {
                'error': 'Claude API key not configured',
                'guitars': [],
                'amps': [],
                'pedals': [],
                'signal_chain': [],
                'confidence_score': 0.0
            }

        if not scraper_results:
            return {
                'error': 'No data to synthesize',
                'guitars': [],
                'amps': [],
                'pedals': [],
                'signal_chain': [],
                'confidence_score': 0.0
            }

        # Build prompt
        prompt = self._build_synthesis_prompt(artist, song, scraper_results)

        try:
            logger.info(f"Calling Claude API for synthesis ({self.model})")

            # Call Claude API
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=0.3,  # Lower temperature for factual consistency
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # Extract text from response
            response_text = response.content[0].text

            logger.info(f"Claude API response received ({len(response_text)} chars)")

            # Parse JSON response
            gear_data = self._parse_claude_response(response_text)

            # Add metadata
            gear_data['claude_response_raw'] = response_text
            gear_data['sources_count'] = len(scraper_results)

            return gear_data

        except Exception as e:
            logger.error(f"Claude API error: {e}", exc_info=True)
            return {
                'error': str(e),
                'guitars': [],
                'amps': [],
                'pedals': [],
                'signal_chain': [],
                'confidence_score': 0.0
            }

    def _build_synthesis_prompt(
        self,
        artist: str,
        song: str,
        scraper_results: List[ScraperResult]
    ) -> str:
        """
        Build Claude prompt with scraped data
        """
        # Convert scraper results to JSON
        sources_data = []
        for result in scraper_results:
            sources_data.append({
                'source': result.source_name,
                'confidence': result.confidence,
                'data': result.data
            })

        prompt = f"""You are a guitar gear expert. Analyze the following information about {artist}'s gear used in the song "{song}".

RAW DATA FROM MULTIPLE SOURCES:
{json.dumps(sources_data, indent=2)}

YOUR TASK:
1. Identify the guitar(s), amp(s), and pedals most likely used in this song
2. Reconstruct the signal chain (order: guitar → pedals in order → amp)
3. Note amp settings if available (gain, EQ, etc.)
4. Provide era-specific context (e.g., "Recorded in 1995, known for using...")
5. Cross-reference sources and identify conflicts or agreements
6. Assign confidence scores (0-100%) to each piece of gear
7. Weight sources by credibility:
   - Highest: Equipboard, YouTube rig rundowns (official interviews)
   - Medium: Forums, Reddit discussions
   - Lower: General web searches

IMPORTANT RULES:
- Only include gear you have evidence for (don't guess)
- If sources conflict, note the conflict and explain your reasoning
- If data is sparse, be honest about low confidence
- Focus on gear specifically for THIS SONG, not just general artist gear
- For signal chain, order pedals logically (compression → overdrive → modulation → delay → reverb)

OUTPUT FORMAT (JSON):
{{
  "guitars": [
    {{
      "make": "Fender",
      "model": "Stratocaster",
      "year": 1965,
      "notes": "Sunburst finish, used in music video",
      "confidence": 85,
      "sources": ["equipboard", "youtube"]
    }}
  ],
  "amps": [
    {{
      "make": "Marshall",
      "model": "JCM800",
      "notes": "Seen in live performances",
      "confidence": 90,
      "sources": ["youtube", "reddit"]
    }}
  ],
  "pedals": [
    {{
      "make": "Boss",
      "model": "DS-1",
      "type": "distortion",
      "confidence": 75,
      "sources": ["reddit", "gearspace"]
    }}
  ],
  "signal_chain": [
    {{"type": "guitar", "item": "Fender Stratocaster"}},
    {{"type": "pedal", "item": "Boss DS-1"}},
    {{"type": "pedal", "item": "MXR Phase 90"}},
    {{"type": "amp", "item": "Marshall JCM800"}}
  ],
  "amp_settings": {{
    "gain": "7/10",
    "treble": "6/10",
    "middle": "5/10",
    "bass": "7/10",
    "notes": "Settings approximated from tone analysis"
  }},
  "context": "This song was recorded in 1995 during the band's experimental phase. The guitar tone is characterized by...",
  "confidence_score": 78,
  "conflicts": [
    {{
      "gear": "Fender Telecaster vs Stratocaster",
      "resolution": "Most sources agree on Stratocaster, Telecaster mention likely refers to different song"
    }}
  ],
  "notes": "Limited data available for this specific song. Gear list based on artist's known setup from the same album/tour."
}}

Return ONLY valid JSON, no additional text.
"""
        return prompt

    def _parse_claude_response(self, response_text: str) -> Dict:
        """
        Parse Claude's JSON response
        """
        try:
            # Remove markdown code blocks if present
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()

            # Parse JSON
            gear_data = json.loads(response_text)

            # Validate required fields
            required_fields = ['guitars', 'amps', 'pedals', 'signal_chain', 'confidence_score']
            for field in required_fields:
                if field not in gear_data:
                    gear_data[field] = [] if field != 'confidence_score' else 0.0

            return gear_data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude response as JSON: {e}")
            logger.debug(f"Response text: {response_text}")
            return {
                'error': 'Failed to parse Claude response',
                'raw_response': response_text,
                'guitars': [],
                'amps': [],
                'pedals': [],
                'signal_chain': [],
                'confidence_score': 0.0
            }
