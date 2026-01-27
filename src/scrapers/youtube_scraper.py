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
                            video_info = {
                                'video_id': video_id,
                                'title': video_title,
                                'description': video_description,
                                'url': f"https://youtube.com/watch?v={video_id}",
                                'channel': item['snippet']['channelTitle']
                            }

                            # Get video transcript/captions (high-value for gear info)
                            transcript = await self._get_video_transcript(video_id)
                            if transcript:
                                video_info['transcript'] = transcript
                                gear_from_transcript = self._extract_gear_from_text(transcript)
                                gear_data['gear_mentions'].extend(gear_from_transcript)
                                logger.info(f"Extracted {len(gear_from_transcript)} gear mentions from transcript")

                            # Get top comments (often contains detailed gear discussions)
                            comments = await self._get_video_comments(video_id, max_results=20)
                            if comments:
                                video_info['comments'] = comments
                                for comment in comments:
                                    gear_from_comment = self._extract_gear_from_text(comment)
                                    gear_data['gear_mentions'].extend(gear_from_comment)
                                logger.info(f"Extracted gear from {len(comments)} comments")

                            gear_data['videos'].append(video_info)

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

    async def _get_video_transcript(self, video_id: str) -> Optional[str]:
        """
        Fetch video captions/transcript using YouTube API
        Costs 50 quota units per request
        """
        try:
            # Get caption tracks for the video
            captions_list = self.youtube.captions().list(
                part='snippet',
                videoId=video_id
            ).execute()

            if not captions_list.get('items'):
                return None

            # Prefer English captions
            caption_id = None
            for caption in captions_list['items']:
                if caption['snippet']['language'] == 'en':
                    caption_id = caption['id']
                    break

            if not caption_id and captions_list['items']:
                # Fallback to first available caption
                caption_id = captions_list['items'][0]['id']

            if caption_id:
                # Note: Downloading captions requires OAuth, not available with API key alone
                # Instead, we'll rely on description and comments
                # This is a limitation but title/description/comments still provide value
                logger.info(f"Found captions for video {video_id}, but download requires OAuth")
                return None

        except HttpError as e:
            logger.warning(f"Error fetching captions for {video_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching captions: {e}")
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
