"""
Artist metadata scraper for gathering contextual information
"""
import logging
import aiohttp
from typing import Optional
from urllib.parse import quote

from src.scrapers.base_scraper import BaseScraper, ScraperResult

logger = logging.getLogger(__name__)


class ArtistMetadataScraper(BaseScraper):
    """
    Scrapes artist metadata from Wikipedia and MusicBrainz
    to provide contextual information for better gear inference
    """

    def __init__(self):
        super().__init__()
        self.source_name = "artist_metadata"
        self.timeout = 20

    async def search(self, artist: str, song: str, year: Optional[int] = None) -> ScraperResult:
        """
        Gather artist metadata from multiple sources

        Args:
            artist: Artist name
            song: Song title (used for album correlation)
            year: Optional year for better accuracy

        Returns:
            ScraperResult with artist metadata
        """
        logger.info(f"Gathering metadata for artist: {artist}")

        metadata = {
            "genre": [],
            "era": self._infer_era_from_year(year) if year else None,
            "known_gear": [],
            "influences": [],
            "production_notes": "",
            "active_years": None,
            "albums": []
        }

        try:
            # Try to get Wikipedia data
            wiki_data = await self._fetch_wikipedia_data(artist)
            if wiki_data:
                metadata["genre"] = wiki_data.get("genres", [])
                metadata["production_notes"] = wiki_data.get("extract", "")[:500]  # Limit to 500 chars

            # Try to get MusicBrainz data
            mb_data = await self._fetch_musicbrainz_data(artist, year)
            if mb_data:
                if mb_data.get("genres"):
                    metadata["genre"].extend(mb_data["genres"])
                metadata["active_years"] = mb_data.get("active_years")
                metadata["albums"] = mb_data.get("albums", [])

            # Remove duplicates from genres (filter to ensure only strings)
            genres_as_strings = [str(g) for g in metadata["genre"] if g]
            metadata["genre"] = list(dict.fromkeys(genres_as_strings))  # Preserves order, removes dupes

            success = bool(metadata["genre"] or metadata["production_notes"] or metadata["albums"])

            return ScraperResult(
                source_name=self.source_name,
                success=success,
                data=metadata,
                confidence=0.7 if success else 0.0
            )

        except Exception as e:
            logger.error(f"Artist metadata scraping failed: {e}", exc_info=True)
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error=str(e),
                confidence=0.0
            )

    async def _fetch_wikipedia_data(self, artist: str) -> Optional[dict]:
        """
        Fetch artist data from Wikipedia API
        """
        try:
            encoded_artist = quote(artist)
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_artist}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Extract genres from categories or content
                        genres = []
                        extract = data.get("extract", "")

                        # Simple genre extraction from text
                        genre_keywords = {
                            "rock": ["rock", "alternative rock", "hard rock", "punk rock"],
                            "blues": ["blues", "blues rock", "rhythm and blues"],
                            "jazz": ["jazz", "fusion", "bebop"],
                            "metal": ["metal", "heavy metal", "thrash metal"],
                            "country": ["country", "country rock"],
                            "pop": ["pop", "pop rock"],
                            "funk": ["funk", "funk rock"],
                            "soul": ["soul", "r&b"]
                        }

                        extract_lower = extract.lower()
                        for main_genre, keywords in genre_keywords.items():
                            for keyword in keywords:
                                if keyword in extract_lower:
                                    genres.append(main_genre.title())
                                    break

                        return {
                            "extract": extract,
                            "genres": list(set(genres))[:3]  # Limit to top 3
                        }
                    else:
                        logger.debug(f"Wikipedia API returned status {response.status} for {artist}")
                        return None

        except Exception as e:
            logger.debug(f"Wikipedia fetch failed for {artist}: {e}")
            return None

    async def _fetch_musicbrainz_data(self, artist: str, year: Optional[int] = None) -> Optional[dict]:
        """
        Fetch artist data from MusicBrainz API

        Note: MusicBrainz API is rate limited (1 request/second)
        In production, implement caching and respect rate limits
        """
        try:
            encoded_artist = quote(artist)
            url = f"https://musicbrainz.org/ws/2/artist/?query={encoded_artist}&fmt=json&limit=1"

            headers = {
                "User-Agent": "GearDetector/1.0 (contact@geardetector.com)"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()

                        if data.get("artists") and len(data["artists"]) > 0:
                            artist_data = data["artists"][0]

                            # Extract relevant information
                            # MusicBrainz tags are dicts like {"name": "rock", "count": 100}
                            tags = artist_data.get("tags", [])[:3] if "tags" in artist_data else []
                            genre_names = [tag["name"].title() if isinstance(tag, dict) else str(tag) for tag in tags]

                            result = {
                                "genres": genre_names,
                                "active_years": None,
                                "albums": []
                            }

                            # Parse life span for active years
                            if "life-span" in artist_data:
                                life_span = artist_data["life-span"]
                                begin = life_span.get("begin")
                                end = life_span.get("end")
                                if begin:
                                    result["active_years"] = f"{begin[:4]}-{end[:4] if end else 'present'}"

                            return result
                    else:
                        logger.debug(f"MusicBrainz API returned status {response.status} for {artist}")
                        return None

        except Exception as e:
            logger.debug(f"MusicBrainz fetch failed for {artist}: {e}")
            return None

    def _infer_era_from_year(self, year: int) -> str:
        """
        Map year to musical era with typical characteristics
        """
        if year < 1960:
            return "1950s - Early electric era"
        elif year < 1970:
            return "1960s - British Invasion / Psychedelic"
        elif year < 1980:
            return "1970s - Classic rock / Progressive"
        elif year < 1990:
            return "1980s - Hair metal / New Wave / Synth"
        elif year < 2000:
            return "1990s - Grunge / Alternative"
        elif year < 2010:
            return "2000s - Post-grunge / Digital integration"
        else:
            return "2010s+ - Modern / Boutique gear era"
