"""
Redis caching service
"""
import redis.asyncio as redis
import json
import logging
from typing import Optional, Any

from src.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Handles Redis caching operations
    """

    def __init__(self):
        self.redis_client = None
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            logger.info("Redis cache client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        """
        if not self.redis_client:
            return None

        try:
            value = await self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Set value in cache with optional TTL
        """
        if not self.redis_client:
            return False

        try:
            ttl = ttl or settings.cache_ttl_seconds
            serialized = json.dumps(value)
            await self.redis_client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache
        """
        if not self.redis_client:
            return False

        try:
            await self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def close(self):
        """
        Close Redis connection
        """
        if self.redis_client:
            await self.redis_client.close()
