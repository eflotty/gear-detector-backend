"""
Gearspace forum scraper - searches Gearspace forums for gear discussions
"""
import httpx
from bs4 import BeautifulSoup
from typing import Optional, List
import logging
import re

from src.scrapers.base_scraper import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


class GearspaceScraper(BaseScraper):
    """
    Scrapes gear discussions from Gearspace forums (formerly Gearslutz)
    """

    BASE_URL = "https://gearspace.com"

    def __init__(self):
        super().__init__()
        self.headers = {
            'User-Agent': 'GearDetectorBot/1.0 (+https://geardetector.com)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }

    async def search(self, artist: str, song: str, year: Optional[int] = None) -> ScraperResult:
        """
        Search Gearspace forums for gear discussions
        """
        try:
            # Build search query
            search_query = f"{artist} {song} gear"
            search_url = f"{self.BASE_URL}/search.php"

            params = {
                'query': search_query,
                'do': 'process'
            }

            async with httpx.AsyncClient(timeout=20) as client:
                # Perform search
                response = await client.get(search_url, params=params, headers=self.headers, follow_redirects=True)

                if response.status_code != 200:
                    return ScraperResult(
                        source_name=self.source_name,
                        success=False,
                        data={},
                        error=f"Search failed with status {response.status_code}"
                    )

                # Parse results
                soup = BeautifulSoup(response.text, 'lxml')

                # Extract gear mentions from search results
                gear_mentions = self._extract_gear_from_page(soup)

                if not gear_mentions:
                    return ScraperResult(
                        source_name=self.source_name,
                        success=False,
                        data={},
                        error="No gear mentions found"
                    )

                return ScraperResult(
                    source_name=self.source_name,
                    success=True,
                    data={'gear_mentions': gear_mentions},
                    confidence=0.7  # Forum discussions are moderately reliable
                )

        except Exception as e:
            logger.error(f"Gearspace scraper error: {e}", exc_info=True)
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error=str(e)
            )

    def _extract_gear_from_page(self, soup: BeautifulSoup) -> List[dict]:
        """
        Extract gear mentions from search results page
        """
        gear_mentions = []

        # Find forum posts or threads
        posts = soup.find_all('div', class_='post') or \
               soup.find_all('div', class_='thread') or \
               soup.find_all('li', class_='result')

        for post in posts[:20]:  # Limit to first 20 results
            text = post.get_text()
            mentions = self._extract_gear_from_text(text)
            gear_mentions.extend(mentions)

        # Remove duplicates and count occurrences
        from collections import Counter
        mention_counts = Counter(gear_mentions)

        return [
            {
                'name': gear,
                'mention_count': count,
                'source': 'gearspace'
            }
            for gear, count in mention_counts.most_common(20)
        ]

    def _extract_gear_from_text(self, text: str) -> List[str]:
        """
        Extract gear names using regex patterns
        """
        gear_patterns = [
            r'\b([A-Z][a-z]+\s+[A-Z]{2,4}-?\d+[a-z]?)\b',
            r'\b(Fender|Marshall|Vox|Orange|Mesa Boogie|Peavey)\s+([A-Z][a-z]+\s*\d*)\b',
            r'\b(Fender|Gibson|Ibanez|PRS|ESP)\s+(Stratocaster|Telecaster|Les Paul|SG)\b'
        ]

        mentions = []
        for pattern in gear_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                gear_name = ' '.join(match) if isinstance(match, tuple) else match
                mentions.append(gear_name.strip())

        return mentions
