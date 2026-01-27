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
from src.scrapers.artist_metadata_scraper import ArtistMetadataScraper

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
            WebSearchScraper(),
            ArtistMetadataScraper()  # Provides contextual info for better inference
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
        logger.info(f"🚀 Starting data aggregation for: {artist} - {song}")
        logger.info(f"📊 Running {len(self.scrapers)} scrapers: {[s.__class__.__name__ for s in self.scrapers]}")

        # Execute all scrapers concurrently with timeout protection
        tasks = [
            scraper.search_with_timeout(artist, song, year)
            for scraper in self.scrapers
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter successful results with detailed logging
        successful_results = []
        for idx, result in enumerate(results):
            scraper_name = self.scrapers[idx].__class__.__name__

            if isinstance(result, ScraperResult) and result.success:
                successful_results.append(result)
                data_summary = str(result.data)[:100] if result.data else "empty"
                logger.info(f"✅ {scraper_name} SUCCESS - Confidence: {result.confidence:.0%}, Data: {data_summary}...")
            elif isinstance(result, ScraperResult):
                logger.warning(f"❌ {scraper_name} FAILED - Error: {result.error}")
            elif isinstance(result, Exception):
                logger.error(f"💥 {scraper_name} EXCEPTION - {type(result).__name__}: {str(result)}")
            else:
                logger.error(f"❓ {scraper_name} UNKNOWN RESULT - {type(result)}: {result}")

        logger.info(f"📈 Data aggregation complete: {len(successful_results)}/{len(self.scrapers)} sources successful")

        if len(successful_results) == 0:
            logger.error("⚠️ WARNING: ALL SCRAPERS FAILED - Check API keys and network connectivity")

        return successful_results
