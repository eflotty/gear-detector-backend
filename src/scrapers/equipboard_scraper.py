"""
Equipboard scraper - extracts gear information from equipboard.com
"""
import httpx
from bs4 import BeautifulSoup
from typing import Optional
import logging
import asyncio
import random

from src.scrapers.base_scraper import BaseScraper, ScraperResult
from src.scrapers.headers import get_browser_headers

logger = logging.getLogger(__name__)


class EquipboardScraper(BaseScraper):
    """
    Scrapes gear information from Equipboard
    """

    BASE_URL = "https://equipboard.com"

    def __init__(self):
        super().__init__()

    async def search(self, artist: str, song: str, year: Optional[int] = None) -> ScraperResult:
        """
        Search Equipboard for artist gear

        Strategy:
        1. Find artist profile page
        2. Extract all gear from profile
        3. Return structured data
        """
        try:
            # Normalize artist name for URL (replace spaces with hyphens, lowercase)
            artist_slug = artist.lower().replace(' ', '-').replace("'", '').replace('.', '')

            # Construct artist profile URL
            artist_url = f"{self.BASE_URL}/pros/{artist_slug}"
            logger.info(f"🎸 Equipboard: Searching for {artist} at {artist_url}")

            # Generate fresh browser headers with referer
            headers = get_browser_headers(referer=self.BASE_URL)

            # Add small delay to mimic human behavior (avoid rate limiting)
            await asyncio.sleep(random.uniform(0.5, 1.5))

            async with httpx.AsyncClient(timeout=20) as client:
                # Fetch artist page
                response = await client.get(artist_url, headers=headers, follow_redirects=True)

                logger.info(f"🌐 Equipboard: HTTP {response.status_code} for {artist}")

                if response.status_code == 404:
                    logger.warning(f"❌ Equipboard: Artist not found: {artist}")
                    return ScraperResult(
                        source_name=self.source_name,
                        success=False,
                        data={},
                        error="Artist not found"
                    )

                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, 'lxml')

                # Extract gear
                gear_data = self._parse_gear_page(soup)

                if not gear_data or not any(gear_data.values()):
                    logger.warning(f"❌ Equipboard: No gear found for {artist}")
                    return ScraperResult(
                        source_name=self.source_name,
                        success=False,
                        data={},
                        error="No gear found"
                    )

                total_items = sum(len(v) for v in gear_data.values() if isinstance(v, list))
                logger.info(f"✅ Equipboard: Found {total_items} gear items for {artist}")

                return ScraperResult(
                    source_name=self.source_name,
                    success=True,
                    data=gear_data,
                    confidence=0.9  # Equipboard is a high-confidence source
                )

        except Exception as e:
            logger.error(f"💥 Equipboard scraper EXCEPTION: {type(e).__name__}: {e}", exc_info=True)
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error=f"{type(e).__name__}: {str(e)}"
            )

    def _parse_gear_page(self, soup: BeautifulSoup) -> dict:
        """
        Parse gear from Equipboard profile page
        """
        gear_data = {
            'guitars': [],
            'amps': [],
            'pedals': [],
            'other': []
        }

        # Find gear items - multiple possible selectors
        gear_items = soup.find_all('div', class_='gear-item') or \
                    soup.find_all('div', class_='product-card') or \
                    soup.find_all('a', class_='gear-link')

        for item in gear_items:
            try:
                # Extract gear name
                name_elem = item.find('h3') or item.find('h4') or \
                           item.find('a', class_='gear-name') or \
                           item.find(class_='product-name')

                if not name_elem:
                    continue

                gear_name = name_elem.get_text(strip=True)

                # Try to find category
                category_elem = item.find('span', class_='category') or \
                              item.find(class_='product-category')
                category = category_elem.get_text(strip=True).lower() if category_elem else gear_name.lower()

                gear_obj = {
                    'name': gear_name,
                    'source': 'equipboard',
                    'url': item.find('a')['href'] if item.find('a') else None
                }

                # Categorize gear
                if any(word in category for word in ['guitar', 'bass', 'fender', 'gibson', 'prs']):
                    gear_data['guitars'].append(gear_obj)
                elif any(word in category for word in ['amp', 'amplifier', 'marshall', 'vox', 'mesa']):
                    gear_data['amps'].append(gear_obj)
                elif any(word in category for word in ['pedal', 'effect', 'stompbox', 'boss', 'mxr']):
                    gear_data['pedals'].append(gear_obj)
                else:
                    gear_data['other'].append(gear_obj)

            except Exception as e:
                logger.warning(f"Error parsing gear item: {e}")
                continue

        return gear_data
