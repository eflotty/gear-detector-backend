"""
Data aggregation service - coordinates all scrapers
"""
import asyncio
from typing import List, Optional
import logging

from src.scrapers.base_scraper import ScraperResult
from src.scrapers.equipboard_scraper import EquipboardScraper
from src.scrapers.reddit_scraper import RedditScraper
from src.scrapers.youtube_scraper import YouTubeScraper
from src.scrapers.gearspace_scraper import GearspaceScraper
from src.scrapers.web_search_scraper import WebSearchScraper

logger = logging.getLogger(__name__)


class DataAggregator:
    """
    Coordinates data collection from all sources
    """

    def __init__(self):
        self.scrapers = [
            EquipboardScraper(),
            RedditScraper(),
            YouTubeScraper(),
            GearspaceScraper(),
            WebSearchScraper()
        ]

    async def aggregate(self, artist: str, song: str, year: Optional[int] = None) -> List[ScraperResult]:
        """
        Run all scrapers in parallel and collect results

        Args:
            artist: Artist name
            song: Song title
            year: Optional year

        Returns:
            List of ScraperResult objects
        """
        logger.info(f"Starting data aggregation for: {artist} - {song}")

        # Execute all scrapers concurrently with timeout protection
        tasks = [
            scraper.search_with_timeout(artist, song, year)
            for scraper in self.scrapers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results
        successful_results = []
        for result in results:
            if isinstance(result, ScraperResult) and result.success:
                successful_results.append(result)
                logger.info(f"✓ {result.source_name} found data")
            elif isinstance(result, ScraperResult):
                logger.warning(f"✗ {result.source_name} failed: {result.error}")
            else:
                logger.error(f"✗ Scraper exception: {result}")

        logger.info(f"Data aggregation complete: {len(successful_results)}/{len(self.scrapers)} sources successful")

        return successful_results
