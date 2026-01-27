"""
Web search fallback scraper - uses SerpAPI to search forums and gear sites
"""
import httpx
from bs4 import BeautifulSoup
from typing import Optional, List, Dict
import logging
import re

from src.scrapers.base_scraper import BaseScraper, ScraperResult
from src.config import settings

logger = logging.getLogger(__name__)


class WebSearchScraper(BaseScraper):
    """
    Uses SerpAPI to search Google for forum discussions and gear mentions
    Focuses on: Gearspace, TGP, Reddit threads, gear forums
    """

    def __init__(self):
        super().__init__()
        self.headers = {
            'User-Agent': 'GearDetectorBot/1.0 (+https://geardetector.com)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
        self.serpapi_enabled = bool(settings.scraper_api_key and settings.scraper_api_key != "xxxxx")

    async def search(self, artist: str, song: str, year: Optional[int] = None) -> ScraperResult:
        """
        Search Google via SerpAPI for forum discussions and gear mentions
        Targets: Gearspace, The Gear Page, Reddit, gear forums
        """
        if not self.serpapi_enabled:
            logger.warning("⚠️ SerpAPI key not configured - web search disabled")
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error="SerpAPI key not configured (SCRAPER_API_KEY)"
            )

        try:
            gear_data = {
                'forum_mentions': [],
                'gear_from_snippets': []
            }

            # Multiple search queries to catch different forum discussions
            search_queries = [
                f'"{artist}" "{song}" guitar gear site:gearspace.com OR site:thegearpage.net',
                f'"{artist}" "{song}" pedals amp rig forum',
                f'"{artist}" gear setup {year if year else ""}'.strip()
            ]

            logger.info(f"🔍 Web search: Starting for {artist} - {song}")

            for query in search_queries[:2]:  # Limit to 2 queries to avoid API quota
                try:
                    results = await self._search_serpapi(query)

                    if results and 'organic_results' in results:
                        for result in results['organic_results'][:10]:  # Top 10 results
                            snippet = result.get('snippet', '')
                            title = result.get('title', '')
                            link = result.get('link', '')

                            # Extract gear mentions from snippets
                            gear_mentions = self._extract_gear_from_text(f"{title} {snippet}")

                            if gear_mentions:
                                gear_data['forum_mentions'].append({
                                    'url': link,
                                    'title': title,
                                    'snippet': snippet,
                                    'gear_found': gear_mentions
                                })
                                gear_data['gear_from_snippets'].extend(gear_mentions)

                except Exception as e:
                    logger.warning(f"SerpAPI query failed: {e}")
                    continue

            # Deduplicate gear mentions
            if gear_data['gear_from_snippets']:
                gear_data['gear_from_snippets'] = list(set(gear_data['gear_from_snippets']))

            if not gear_data['forum_mentions']:
                logger.info(f"❌ Web search: No forum results found for {artist}")
                return ScraperResult(
                    source_name=self.source_name,
                    success=False,
                    data={},
                    error="No relevant forum discussions found"
                )

            logger.info(f"✅ Web search: Found {len(gear_data['forum_mentions'])} forum mentions, {len(gear_data['gear_from_snippets'])} gear items")

            return ScraperResult(
                source_name=self.source_name,
                success=True,
                data=gear_data,
                confidence=0.6  # Forum data is medium confidence
            )

        except Exception as e:
            logger.error(f"💥 Web search scraper error: {e}", exc_info=True)
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error=str(e)
            )

    async def _search_serpapi(self, query: str) -> Optional[Dict]:
        """
        Call SerpAPI to get Google search results
        """
        try:
            params = {
                'q': query,
                'api_key': settings.scraper_api_key,
                'num': 10,
                'engine': 'google'
            }

            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(
                    'https://serpapi.com/search',
                    params=params
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"SerpAPI HTTP error: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"SerpAPI request failed: {e}")
            return None

    def _extract_gear_from_text(self, text: str) -> List[str]:
        """
        Extract gear names using regex patterns
        Enhanced for forum discussions
        """
        gear_patterns = [
            # Pedal model numbers (e.g., "MXR Phase 90", "Boss CE-2")
            r'\b([A-Z][a-z]+\s+[A-Z]{2,4}-?\d+[a-zA-Z]*)\b',

            # Amp brands + models
            r'\b(Fender|Marshall|Vox|Orange|Mesa Boogie|Mesa|Peavey|Friedman|Diezel|Soldano|Bogner|Dumble)\s+([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)?)\b',

            # Guitar brands + models
            r'\b(Fender|Gibson|Ibanez|PRS|ESP|Gretsch|Rickenbacker|Music Man)\s+(Stratocaster|Telecaster|Les Paul|SG|RG|Custom\s+24|Explorer|Flying\s+V)\b',

            # Common pedal names
            r'\b(Tube Screamer|Klon|Big Muff|Rat|Blues Driver|Centaur|King of Tone|Timmy)\b',

            # Pedal brand + type
            r'\b(Boss|MXR|Electro-Harmonix|Strymon|Walrus Audio|Earthquaker|JHS|Fulltone|Way Huge)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b'
        ]

        mentions = []
        for pattern in gear_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    gear_name = ' '.join(m for m in match if m).strip()
                else:
                    gear_name = match.strip()

                if gear_name and len(gear_name) > 2:  # Avoid single letters
                    mentions.append(gear_name)

        return mentions
