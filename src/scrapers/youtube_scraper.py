"""
YouTube Data API scraper - searches for rig rundown videos and gear discussions
"""
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Optional, List
import logging
import re

from src.scrapers.base_scraper import BaseScraper, ScraperResult
from src.config import settings

logger = logging.getLogger(__name__)


class YouTubeScraper(BaseScraper):
    """
    Searches YouTube for gear-related videos using YouTube Data API v3
    """

    def __init__(self):
        super().__init__()
        self.youtube = None
        if settings.youtube_api_key:
            try:
                self.youtube = build('youtube', 'v3', developerKey=settings.youtube_api_key)
                logger.info("YouTube API client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize YouTube client: {e}")

    async def search(self, artist: str, song: str, year: Optional[int] = None) -> ScraperResult:
        """
        Search YouTube for rig rundown and gear videos
        """
        if not self.youtube:
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error="YouTube API not configured"
            )

        try:
            gear_data = {
                'videos': [],
                'gear_mentions': []
            }

            # Search queries
            queries = [
                f"{artist} rig rundown",
                f"{artist} {song} guitar tone",
                f"{artist} guitar gear"
            ]

            for query in queries:
                try:
                    # Search videos (costs 100 quota units per search)
                    search_response = self.youtube.search().list(
                        q=query,
                        part='id,snippet',
                        maxResults=5,  # Limit to conserve quota
                        type='video',
                        order='relevance'
                    ).execute()

                    for item in search_response.get('items', []):
                        video_id = item['id']['videoId']
                        video_title = item['snippet']['title']
                        video_description = item['snippet']['description']

                        # Get video details (costs 1 quota unit)
                        video_details = self.youtube.videos().list(
                            part='snippet,statistics',
                            id=video_id
                        ).execute()

                        if video_details['items']:
                            gear_data['videos'].append({
                                'video_id': video_id,
                                'title': video_title,
                                'description': video_description,
                                'url': f"https://youtube.com/watch?v={video_id}",
                                'channel': item['snippet']['channelTitle']
                            })

                            # Extract gear from title and description
                            combined_text = f"{video_title} {video_description}"
                            gear_mentions = self._extract_gear_from_text(combined_text)
                            gear_data['gear_mentions'].extend(gear_mentions)

                except HttpError as e:
                    logger.warning(f"YouTube search error for '{query}': {e}")
                    continue

            if not gear_data['videos']:
                return ScraperResult(
                    source_name=self.source_name,
                    success=False,
                    data={},
                    error="No relevant videos found"
                )

            # Deduplicate gear mentions
            gear_data['gear_mentions'] = list(set(gear_data['gear_mentions']))

            return ScraperResult(
                source_name=self.source_name,
                success=True,
                data=gear_data,
                confidence=0.8  # YouTube rig rundowns are high confidence
            )

        except Exception as e:
            logger.error(f"YouTube scraper error: {e}", exc_info=True)
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error=str(e)
            )

    def _extract_gear_from_text(self, text: str) -> List[str]:
        """
        Extract gear mentions using regex patterns
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
