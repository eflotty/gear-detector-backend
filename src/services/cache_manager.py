"""
Cache manager for photo search results
Uses Redis for fast caching of vision API responses
"""
import redis.asyncio as redis
import json
import logging
from typing import Optional, Dict
from datetime import timedelta

from src.config import settings

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages Redis caching for photo search results"""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.enabled = True

    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis_client = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis for caching")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}. Caching disabled.")
            self.enabled = False

    async def disconnect(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")

    async def get_photo_result(self, image_hash: str) -> Optional[Dict]:
        """
        Get cached photo search result

        Args:
            image_hash: SHA256 hash of the image

        Returns:
            Cached gear data dict or None if not found
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            key = f"photo:{image_hash}"
            cached = await self.redis_client.get(key)

            if cached:
                logger.info(f"✅ Redis cache hit for photo: {image_hash[:16]}...")
                return json.loads(cached)

            return None

        except Exception as e:
            logger.warning(f"Redis get error: {e}")
            return None

    async def set_photo_result(
        self,
        image_hash: str,
        gear_data: Dict,
        ttl_days: int = 90
    ) -> bool:
        """
        Cache photo search result

        Args:
            image_hash: SHA256 hash of the image
            gear_data: Gear identification result
            ttl_days: Time to live in days (default 90)

        Returns:
            True if cached successfully
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            key = f"photo:{image_hash}"
            value = json.dumps(gear_data)
            ttl = timedelta(days=ttl_days)

            await self.redis_client.setex(key, ttl, value)
            logger.info(f"💾 Cached photo result: {image_hash[:16]}... (TTL: {ttl_days}d)")
            return True

        except Exception as e:
            logger.warning(f"Redis set error: {e}")
            return False

    async def delete_photo_result(self, image_hash: str) -> bool:
        """
        Delete cached photo search result
        Used to clear bad cached data (e.g., validation errors)

        Args:
            image_hash: SHA256 hash of the image

        Returns:
            True if deleted successfully
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            key = f"photo:{image_hash}"
            deleted = await self.redis_client.delete(key)
            if deleted:
                logger.info(f"🗑️ Deleted cached photo result: {image_hash[:16]}...")
            return deleted > 0

        except Exception as e:
            logger.warning(f"Redis delete error: {e}")
            return False

    async def get_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.enabled or not self.redis_client:
            return {"enabled": False}

        try:
            info = await self.redis_client.info()
            return {
                "enabled": True,
                "connected": True,
                "used_memory": info.get("used_memory_human"),
                "total_keys": await self.redis_client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0)
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"enabled": True, "connected": False, "error": str(e)}


# Global cache manager instance
cache_manager = CacheManager()
