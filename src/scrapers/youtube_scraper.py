"""
YouTube Data API scraper - searches for rig rundown videos and gear discussions
"""
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
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

        # Check if API key is configured
        if not settings.youtube_api_key:
            logger.warning("⚠️ YouTube API key not configured (YOUTUBE_API_KEY not set)")
        elif settings.youtube_api_key == "xxxxx":
            logger.warning("⚠️ YouTube API key is placeholder value 'xxxxx' - needs real API key")
        else:
            try:
                key_preview = settings.youtube_api_key[:8] + "..." if len(settings.youtube_api_key) > 8 else "too_short"
                logger.info(f"🔑 YouTube API key found: {key_preview}")
                self.youtube = build('youtube', 'v3', developerKey=settings.youtube_api_key)
                logger.info("✅ YouTube API client initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize YouTube client: {e}")

    async def search(self, artist: str, song: str, year: Optional[int] = None) -> ScraperResult:
        """
        Search YouTube for rig rundown and gear videos
        """
        if not self.youtube:
            error_msg = "YouTube API not configured - check YOUTUBE_API_KEY environment variable"
            logger.error(f"❌ YouTube search failed: {error_msg}")
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error=error_msg
            )

        logger.info(f"🎬 YouTube: Starting search for {artist} - {song}")

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

            for query_index, query in enumerate(queries):
                try:
                    logger.info(f"🔍 YouTube: Query {query_index + 1}/3: '{query}'")
                    # Search videos (costs 100 quota units per search)
                    search_response = self.youtube.search().list(
                        q=query,
                        part='id,snippet',
                        maxResults=5,  # Limit to conserve quota
                        type='video',
                        order='relevance'
                    ).execute()

                    video_count = len(search_response.get('items', []))
                    logger.info(f"📹 YouTube: Found {video_count} videos for query '{query}'")

                    for video_index, item in enumerate(search_response.get('items', [])):
                        video_id = item['id']['videoId']
                        video_title = item['snippet']['title']
                        video_description = item['snippet']['description']

                        # Get video details (costs 1 quota unit)
                        video_details = self.youtube.videos().list(
                            part='snippet,statistics',
                            id=video_id
                        ).execute()

                        if video_details['items']:
                            video_info = {
                                'video_id': video_id,
                                'title': video_title,
                                'description': video_description,
                                'url': f"https://youtube.com/watch?v={video_id}",
                                'channel': item['snippet']['channelTitle']
                            }

                            # Only fetch transcript from the TOP video of the FIRST query (most relevant)
                            # This provides high-value data while keeping API usage reasonable
                            if query_index == 0 and video_index == 0:
                                transcript = await self._get_video_transcript(video_id)
                                if transcript:
                                    video_info['transcript'] = transcript
                                    gear_from_transcript = self._extract_gear_from_text(transcript)
                                    gear_data['gear_mentions'].extend(gear_from_transcript)
                                    logger.info(f"🎬 Extracted {len(gear_from_transcript)} gear mentions from transcript")

                            # Get top comments from all videos (lightweight, 1 quota unit each)
                            comments = await self._get_video_comments(video_id, max_results=20)
                            if comments:
                                video_info['comments'] = comments
                                for comment in comments:
                                    gear_from_comment = self._extract_gear_from_text(comment)
                                    gear_data['gear_mentions'].extend(gear_from_comment)
                                if video_index == 0:
                                    logger.info(f"💬 Extracted gear from {len(comments)} comments")

                            gear_data['videos'].append(video_info)

                            # Extract gear from title and description
                            combined_text = f"{video_title} {video_description}"
                            gear_mentions = self._extract_gear_from_text(combined_text)
                            gear_data['gear_mentions'].extend(gear_mentions)

                except HttpError as e:
                    logger.warning(f"YouTube search error for '{query}': {e}")
                    continue

            if not gear_data['videos']:
                logger.warning(f"❌ YouTube: No relevant videos found for {artist} - {song}")
                return ScraperResult(
                    source_name=self.source_name,
                    success=False,
                    data={},
                    error="No relevant videos found"
                )

            # Deduplicate gear mentions
            gear_data['gear_mentions'] = list(set(gear_data['gear_mentions']))

            logger.info(f"✅ YouTube: Found {len(gear_data['videos'])} videos, {len(gear_data['gear_mentions'])} unique gear mentions")

            return ScraperResult(
                source_name=self.source_name,
                success=True,
                data=gear_data,
                confidence=0.8  # YouTube rig rundowns are high confidence
            )

        except Exception as e:
            logger.error(f"💥 YouTube scraper EXCEPTION: {type(e).__name__}: {e}", exc_info=True)
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error=f"{type(e).__name__}: {str(e)}"
            )

    async def _get_video_transcript(self, video_id: str) -> Optional[str]:
        """
        Fetch video transcript using youtube-transcript-api
        This works without OAuth - scrapes YouTube's transcript endpoint directly
        """
        try:
            # Get transcript (tries auto-generated if manual not available)
            transcript_list = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=['en', 'en-US', 'en-GB']  # Prefer English
            )

            # Combine all transcript entries into one text
            full_transcript = ' '.join([entry['text'] for entry in transcript_list])

            logger.info(f"Successfully fetched transcript for {video_id} ({len(full_transcript)} chars)")
            return full_transcript

        except Exception as e:
            # Transcript not available (disabled, private video, etc.)
            logger.debug(f"Could not fetch transcript for {video_id}: {e}")
            return None

    async def _get_video_comments(self, video_id: str, max_results: int = 20) -> List[str]:
        """
        Fetch top comments from a video
        Costs 1 quota unit per request
        """
        try:
            comments_response = self.youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=max_results,
                order='relevance',  # Get most relevant/liked comments
                textFormat='plainText'
            ).execute()

            comments = []
            for item in comments_response.get('items', []):
                comment_text = item['snippet']['topLevelComment']['snippet']['textDisplay']
                comments.append(comment_text)

            return comments

        except HttpError as e:
            # Comments may be disabled
            logger.warning(f"Could not fetch comments for {video_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching comments: {e}")
            return []

    def _extract_gear_from_text(self, text: str) -> List[str]:
        """
        Extract gear mentions using regex patterns
        """
        gear_patterns = [
            r'\b([A-Z][a-z]+\s+[A-Z]{2,4}-?\d+[a-z]?)\b',
            r'\b(Fender|Marshall|Vox|Orange|Mesa Boogie|Peavey)\s+([A-Z][a-z]+\s*\d*)\b',
            r'\b(Fender|Gibson|Ibanez|PRS|ESP)\s+(Stratocaster|Telecaster|Les Paul|SG)\b',
            r'\b(Tube Screamer|Klon|Big Muff|Rat|Boss|MXR|Electro-Harmonix)\b'
        ]

        mentions = []
        for pattern in gear_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                gear_name = ' '.join(match) if isinstance(match, tuple) else match
                mentions.append(gear_name.strip())

        return mentions
