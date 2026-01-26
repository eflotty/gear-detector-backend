"""
Abstract base class for all scrapers
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import logging
import asyncio
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ScraperResult:
    """
    Standardized result format from scrapers
    """
    source_name: str
    success: bool
    data: Dict
    error: Optional[str] = None
    confidence: float = 0.0


class BaseScraper(ABC):
    """
    Base class that all scrapers must inherit from
    """

    def __init__(self):
        self.source_name = self.__class__.__name__.replace('Scraper', '').lower()
        self.timeout = 30  # seconds

    @abstractmethod
    async def search(self, artist: str, song: str, year: Optional[int] = None) -> ScraperResult:
        """
        Search for gear information

        Args:
            artist: Artist name
            song: Song title
            year: Optional year for better search accuracy

        Returns:
            ScraperResult with found gear information
        """
        pass

    async def search_with_timeout(self, artist: str, song: str, year: Optional[int] = None) -> ScraperResult:
        """
        Execute search with timeout protection
        """
        try:
            return await asyncio.wait_for(
                self.search(artist, song, year),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"{self.source_name} search timed out after {self.timeout}s")
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error="Timeout"
            )
        except Exception as e:
            logger.error(f"{self.source_name} search failed: {e}", exc_info=True)
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error=str(e)
            )
