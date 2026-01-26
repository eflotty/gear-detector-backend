"""
Reddit API scraper - searches guitar-related subreddits for gear information
"""
import praw
from typing import Optional, List
import logging
import re
from collections import Counter

from src.scrapers.base_scraper import BaseScraper, ScraperResult
from src.config import settings

logger = logging.getLogger(__name__)


class RedditScraper(BaseScraper):
    """
    Searches Reddit for gear information using PRAW (Python Reddit API Wrapper)
    """

    SUBREDDITS = [
        'guitarpedals',
        'synthesizers',
        'WeAreTheMusicMakers',
        'Guitar',
        'Bass',
        'audioengineering'
    ]

    def __init__(self):
        super().__init__()
        self.reddit = None
        if settings.reddit_client_id and settings.reddit_client_secret:
            try:
                self.reddit = praw.Reddit(
                    client_id=settings.reddit_client_id,
                    client_secret=settings.reddit_client_secret,
                    user_agent=settings.scraper_user_agent
                )
                logger.info("Reddit API client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Reddit client: {e}")

    async def search(self, artist: str, song: str, year: Optional[int] = None) -> ScraperResult:
        """
        Search Reddit for gear discussions
        """
        if not self.reddit:
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error="Reddit API not configured"
            )

        try:
            # Build search query
            query = f'"{artist}" "{song}" gear'

            gear_mentions = []

            # Search across subreddits
            for subreddit_name in self.SUBREDDITS:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)

                    # Search (limit to top 20 results to stay within rate limits)
                    for submission in subreddit.search(query, limit=20, sort='relevance'):
                        # Extract gear from title and selftext
                        post_gear = self._extract_gear_from_text(
                            submission.title + ' ' + (submission.selftext or '')
                        )

                        if post_gear:
                            gear_mentions.extend(post_gear)

                        # Also check top comments
                        submission.comments.replace_more(limit=0)  # Don't load "more comments"
                        for comment in submission.comments.list()[:10]:  # Top 10 comments
                            comment_gear = self._extract_gear_from_text(comment.body)
                            if comment_gear:
                                gear_mentions.extend(comment_gear)

                except Exception as e:
                    logger.warning(f"Error searching r/{subreddit_name}: {e}")
                    continue

            if not gear_mentions:
                return ScraperResult(
                    source_name=self.source_name,
                    success=False,
                    data={},
                    error="No gear mentions found"
                )

            # Organize gear by frequency (most mentioned = more likely)
            gear_data = self._organize_gear_mentions(gear_mentions)

            return ScraperResult(
                source_name=self.source_name,
                success=True,
                data=gear_data,
                confidence=0.6  # Reddit is medium confidence (user-generated content)
            )

        except Exception as e:
            logger.error(f"Reddit scraper error: {e}", exc_info=True)
            return ScraperResult(
                source_name=self.source_name,
                success=False,
                data={},
                error=str(e)
            )

    def _extract_gear_from_text(self, text: str) -> List[str]:
        """
        Extract potential gear mentions from text using regex patterns
        """
        gear_patterns = [
            # Pedal patterns (e.g., "Boss DS-1", "Ibanez TS9")
            r'\b([A-Z][a-z]+\s+[A-Z]{2,4}-?\d+[a-z]?)\b',
            # Amp patterns (e.g., "Fender Twin Reverb", "Marshall JCM800")
            r'\b(Fender|Marshall|Vox|Orange|Mesa Boogie|Peavey)\s+([A-Z][a-z]+\s*\d*)\b',
            # Guitar patterns
            r'\b(Fender|Gibson|Ibanez|PRS|ESP)\s+(Stratocaster|Telecaster|Les Paul|SG|[A-Z]{2,})\b'
        ]

        mentions = []
        for pattern in gear_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Join tuple matches
                gear_name = ' '.join(match) if isinstance(match, tuple) else match
                mentions.append(gear_name.strip())

        return mentions

    def _organize_gear_mentions(self, mentions: List[str]) -> dict:
        """
        Count and organize gear mentions
        """
        mention_counts = Counter(mentions)

        # Most mentioned gear (top 20)
        top_gear = mention_counts.most_common(20)

        return {
            'gear_mentions': [
                {
                    'name': gear,
                    'mention_count': count,
                    'source': 'reddit'
                }
                for gear, count in top_gear
            ]
        }
