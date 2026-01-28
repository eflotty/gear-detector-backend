"""
Claude AI service for synthesizing gear data
"""
from anthropic import AsyncAnthropic
from typing import List, Dict, Optional
import json
import logging

from src.scrapers.base_scraper import ScraperResult
from src.services.context_service import ContextService
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
        self.context_service = ContextService()

    async def synthesize_gear_data(
        self,
        artist: str,
        song: str,
        scraper_results: List[ScraperResult],
        year: Optional[int] = None
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
            logger.error("Claude API not configured - cannot synthesize")
            raise ValueError("Claude API key not configured. Please set ANTHROPIC_API_KEY in environment variables.")

        # Allow synthesis even with no scraper results - Claude can use its knowledge
        if not scraper_results:
            logger.warning(f"No scraper data available for {artist} - {song}. Using pure Claude inference from its knowledge base.")

        # Get artist context for better inference
        artist_context = await self.context_service.get_artist_context(artist, song, year)

        # Build prompt with context
        prompt = self._build_synthesis_prompt(artist, song, scraper_results, artist_context)

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
        scraper_results: List[ScraperResult],
        context: Dict
    ) -> str:
        """
        Build Claude prompt with scraped data and artist context
        """
        # Convert scraper results to JSON
        sources_data = []
        for result in scraper_results:
            sources_data.append({
                'source': result.source_name,
                'confidence': result.confidence,
                'data': result.data
            })

        # Format context for prompt
        context_text = self.context_service.format_context_for_prompt(context)

        # Determine if we have any scraper data
        has_scraper_data = len(sources_data) > 0
        data_source_section = ""

        if has_scraper_data:
            data_source_section = f"""RAW DATA FROM MULTIPLE SOURCES:
{json.dumps(sources_data, indent=2)}

⚠️ **IMPORTANT**: Use the above data as your PRIMARY source of truth.
- Include ALL gear explicitly mentioned in the source data
- Assign high confidence (90-100%) to gear found in multiple sources or high-quality sources
- Only supplement with your knowledge if source data is clearly incomplete
- DO NOT add alternatives or "similar" gear unless found in sources"""
        else:
            data_source_section = f"""⚠️ NO SCRAPER DATA AVAILABLE - Use pure inference from your knowledge base.

You must use your extensive knowledge of {artist}'s gear, playing style, and the era/album this song is from.
Base your analysis on:
- Artist's documented signature gear and preferences
- Genre conventions and typical gear for this style
- Album/era production characteristics
- Your knowledge of this specific song and its tone

Mark all items with appropriate confidence levels (likely use "Inferred" 50-69% or "Likely" 70-89% unless you have strong knowledge of confirmed gear for this artist/song)."""

        prompt = f"""You are an expert guitar gear analyst with deep knowledge of artists, gear, and music production. Analyze the following information about {artist}'s gear used in the song "{song}".

{context_text}

{data_source_section}

YOUR TASK - CRITICAL REQUIREMENTS:
Provide gear information with a STRONG PREFERENCE for confirmed/documented gear over inference.

1. **ALWAYS provide complete amp settings** (gain, treble, middle, bass, presence) - infer from tone if not explicitly stated
2. **ALWAYS provide a complete signal chain** - construct from detected gear or infer based on genre/artist signature sound
3. Identify guitars, amps, and pedals with confidence levels
4. Provide context explaining your reasoning, especially for inferred items

⚠️ **GEAR SELECTION PRIORITY** (follow this order strictly - QUALITY OVER QUANTITY):
1. **FIRST PRIORITY - OFFICIAL/CONFIRMED GEAR ONLY**: Include gear explicitly mentioned in high-quality sources
   - Equipboard, Premier Guitar rig rundowns, official interviews, verified photos
   - YouTube rig rundown videos from official channels or the artist themselves
   - If multiple sources confirm the same item → Very high confidence (95-100%)
   - If one reliable source documents it → High confidence (85-95%)

2. **BE SELECTIVE WITH SOURCE DATA**:
   - If sources document 3-5 pedals from official rig rundowns → List those specific pedals ONLY
   - If sources document 10+ pedals but some are from low-quality sources (random forums) → FILTER to official/confirmed only
   - DO NOT list every pedal mentioned in casual forum speculation
   - Forum/Reddit mentions should supplement official sources, not drive the list

3. **ARTIST SIGNATURE GEAR** (only when directly relevant):
   - Add well-known signature gear (e.g., "John Mayer = Two Rock amp, Ibanez Tube Screamer")
   - ONLY if it matches the song's era and there's strong evidence it was used for this recording

4. **MINIMAL INFERENCE** (last resort):
   - Only infer when source data is genuinely sparse AND setup seems incomplete
   - Example: Sources confirm guitar + amp but clearly hear overdrive → Infer ONE likely overdrive pedal
   - DO NOT infer just to have a longer list
   - NEVER list "alternatives" or "could be" options

CONFIDENCE LEVELS (use these three tiers):
- **Confirmed** (90-100%): Direct evidence from sources (rig rundowns, interviews, photos)
- **Likely** (70-89%): Strong circumstantial evidence or artist's known signature gear from same era
- **Inferred** (50-69%): Educated inference based on tone, genre, artist style, or similar songs

⚠️ **CRITICAL: AVOID GEAR SPRAWL** (with more data sources, be MORE selective):
- **DO NOT** list every pedal mentioned across all sources - filter for quality
- **DO NOT** list every pedal that COULD produce the effect - only what was ACTUALLY used
- **DO NOT** add "alternatives" or "similar" gear
- **DO NOT** infer pedals just because they're common in the genre
- **DO NOT** pad the list to reach a certain number of items
- **PRIORITIZE**: 3-6 confirmed/official pedals > 15+ mixed-quality mentions
- **Remember**: Users want THE ACTUAL GEAR, not every possible option

INFERENCE GUIDELINES - Only when explicit data is truly missing:
1. **Artist's signature sound and known gear preferences** (e.g., "Eddie Van Halen = EVH Frankenstein + Marshall")
2. **Album/era production characteristics** (e.g., "1980s metal = high gain, scooped mids")
3. **Genre conventions** (e.g., blues rock = tube screamer, jazz = clean amp with reverb) - USE SPARINGLY
4. **Similar songs from the same artist/period**
5. **Tone analysis from the recording** (bright/warm/dark, clean/overdriven/distorted)

AMP SETTINGS INFERENCE RULES:
- **Clean tone**: Lower gain (2-4), balanced EQ, possible slight treble boost
- **Blues/Classic Rock**: Medium gain (5-7), mid-focused, slight treble boost
- **Hard Rock/Metal**: High gain (8-10), scooped mids, higher bass and treble
- **Use tone descriptors** ("bright" = more treble, "warm" = more bass/less treble, "crunchy" = medium gain)
- **Reference amp characteristics** (Fender = clean/scooped, Marshall = mid-focused crunch, Mesa = high gain)

SIGNAL CHAIN CONSTRUCTION:
- Standard order: Guitar → Tuner → Compression → Overdrive/Distortion → Modulation (chorus/flanger) → Delay → Reverb → Amp
- **ONLY include pedals that are confirmed from official sources or well-documented for this artist**
- For high-confidence searches with official rig rundowns: Include all confirmed pedals from the rundown
- For moderate-confidence searches: Include 3-6 most likely/documented pedals - avoid speculation
- For low-confidence searches: Include guitar → amp direct if no solid pedal data exists
- **Quality benchmark**: Prefer "Guitar → Amp (direct)" over listing 8 guessed pedals
- **Remember**: A simple, accurate chain is better than a complex, speculative one

SOURCE CREDIBILITY WEIGHTING:
- Highest: Equipboard, YouTube rig rundowns, official interviews, artist social media
- Medium: Forums (Gearslutz/Gearspace), Reddit discussions, music journalism
- Lower: General web searches, unmarked forum posts

OUTPUT FORMAT (JSON) - ALL FIELDS REQUIRED:
{{
  "guitars": [
    {{
      "make": "Fender",
      "model": "Stratocaster",
      "year": 1965,
      "notes": "Sunburst finish, known from music video. [Confirmed - seen in official footage]",
      "confidence": 95.0,
      "sources": ["equipboard", "youtube"]
    }}
  ],
  "amps": [
    {{
      "make": "Dumble",
      "model": "Overdrive Special",
      "notes": "Artist's signature amp, used throughout this album. [Likely - documented for album sessions]",
      "confidence": 85.0,
      "sources": ["interviews", "producer_notes"]
    }}
  ],
  "pedals": [
    {{
      "make": "Ibanez",
      "model": "TS808 Tube Screamer",
      "type": "Overdrive",
      "confidence": 90.0,
      "sources": ["equipboard"]
    }},
    {{
      "make": "TC Electronic",
      "model": "Flashback",
      "type": "Delay",
      "confidence": 65.0,
      "sources": ["inferred_from_tone"]
    }}
  ],
  "signal_chain": [
    {{"type": "guitar", "item": "Fender Stratocaster (1965)"}},
    {{"type": "pedal", "item": "Ibanez TS808 Tube Screamer"}},
    {{"type": "pedal", "item": "TC Electronic Flashback"}},
    {{"type": "amp", "item": "Dumble Overdrive Special"}}
  ],
  "amp_settings": {{
    "gain": "Medium (5-6)",
    "treble": "7",
    "middle": "5",
    "bass": "6",
    "presence": "5",
    "notes": "Clean headroom with slight breakup. Settings inferred from warm, articulate tone with clarity."
  }},
  "context": "Recorded in 2006 for the Continuum album. The tone features warm, bluesy overdrive with exceptional clarity. This era showcases the artist's signature Stratocaster + Dumble combination, delivering that characteristic smooth, articulate sound with just enough grit. The subtle delay adds depth without overwhelming the natural tone.",
  "confidence_score": 82.0,
  "reasoning": {{
    "guitars": "Confirmed through video evidence and artist interviews from this period.",
    "amps": "Artist's documented signature amp. While not explicitly confirmed for this specific song, used consistently throughout the album.",
    "pedals": "Tube Screamer confirmed via gear database. Delay pedal inferred from recorded tone - characteristic digital delay sound matches TC Electronic profile.",
    "amp_settings": "Inferred from tone analysis. The warm, slightly overdriven sound with strong clarity suggests moderate gain (5-6) with balanced EQ and slight treble emphasis."
  }}
}}

⚠️ **CONFIDENCE SCORING - BE CONSERVATIVE**:
- **Overall confidence_score**: Average the individual gear confidence scores
- **If most gear is "Unknown" or highly inferred**: confidence_score should be 15-30%
- **If mix of confirmed and inferred**: confidence_score should be 40-60%
- **If mostly confirmed from sources**: confidence_score should be 70-90%
- **Never give high confidence (>50%) when returning generic/unknown gear**

⚠️ **CONTEXT FIELD - USER-FACING TONE**:
The "context" field is displayed directly to users. Write it like a knowledgeable music expert, NOT an AI:
- ✅ GOOD: "This track showcases classic 90s grunge tone with heavily overdriven amps and minimal effects. The raw, aggressive sound relies on high-gain amps pushed hard."
- ❌ BAD: "No specific gear is documented in the provided sources for this particular performance. The YouTube data contains no relevant information."
- ✅ GOOD: "Live performance featuring clean, rhythmic guitar work with subtle chorus and ambient reverb"
- ❌ BAD: "Given the live studio session context and the nature of the original song, the setup would likely emphasize clean tones"
- Focus on the SOUND and STYLE, not your uncertainty
- Be confident and informative, even when inferring
- Don't mention data limitations or source quality

**CRITICAL REQUIREMENTS - You MUST include**:
- At least one guitar (prefer confirmed from sources, infer only if absolutely needed)
- At least one amp (prefer confirmed from sources, infer only if absolutely needed)
- Complete signal_chain with detected gear in logical order (avoid padding with inferred pedals)
- Complete amp_settings with ALL parameters (gain, treble, middle, bass, presence, notes)
- **Context field**: User-facing description of the tone/style (sound confident, focus on music, not data limitations)
- **Reasoning field**: Technical explanation of your confidence levels and sources (internal use only)
- **Each gear item MUST have individual confidence score** - be honest about uncertainty
- **Overall confidence_score**: Must reflect actual certainty (20% for mostly unknown, 80% for mostly confirmed)

Return ONLY valid JSON, no additional text before or after.
"""
        return prompt

    def _parse_claude_response(self, response_text: str) -> Dict:
        """
        Parse Claude's JSON response with error correction
        """
        try:
            # Remove markdown code blocks if present
            if '```json' in response_text:
                response_text = response_text.split('```json')[1].split('```')[0].strip()
            elif '```' in response_text:
                response_text = response_text.split('```')[1].split('```')[0].strip()

            # Try to parse JSON
            try:
                gear_data = json.loads(response_text)
            except json.JSONDecodeError as e:
                # Haiku sometimes makes JSON syntax errors - try to fix common issues
                logger.warning(f"Initial JSON parse failed: {e}. Attempting to repair...")

                # Common fixes for Haiku's JSON mistakes
                fixed_text = response_text

                # Fix trailing commas before closing braces/brackets
                fixed_text = fixed_text.replace(',]', ']').replace(',}', '}')

                # Fix missing commas between objects (common Haiku mistake)
                import re
                # Add comma between } and { if missing
                fixed_text = re.sub(r'\}\s*\{', '},{', fixed_text)
                # Add comma between } and " if missing (end of object, start of next key)
                fixed_text = re.sub(r'\}(\s*)"', r'},\1"', fixed_text)

                # Try parsing again
                gear_data = json.loads(fixed_text)
                logger.info("✅ Successfully repaired malformed JSON from Claude")

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
