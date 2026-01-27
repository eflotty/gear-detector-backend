"""
Health check endpoint
"""
from fastapi import APIRouter, status
from pydantic import BaseModel
import redis.asyncio as redis
from sqlalchemy import text

from src.config import settings
from src.database.connection import get_db_session

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    redis_cache: str


class ConfigStatusResponse(BaseModel):
    """API configuration status"""
    anthropic_api: str
    youtube_api: str
    reddit_api: str
    scraper_api: str


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint to verify API and dependencies are running
    """
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "database": "unknown",
        "redis_cache": "unknown"
    }

    # Check database connection
    try:
        async with get_db_session() as session:
            await session.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    # Check Redis connection
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        health_status["redis_cache"] = "connected"
    except Exception as e:
        health_status["redis_cache"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"

    return health_status


@router.get("/config-status", response_model=ConfigStatusResponse, status_code=status.HTTP_200_OK)
async def config_status():
    """
    Check which API keys are configured (without exposing the actual keys)
    """
    def check_key(key: str) -> str:
        if not key:
            return "❌ NOT SET"
        elif key == "xxxxx" or key.startswith("sk-ant-xxxxx"):
            return "⚠️ PLACEHOLDER (not real key)"
        elif len(key) > 10:
            return f"✅ CONFIGURED ({key[:8]}...)"
        else:
            return "⚠️ TOO SHORT (invalid)"

    return ConfigStatusResponse(
        anthropic_api=check_key(settings.anthropic_api_key),
        youtube_api=check_key(settings.youtube_api_key),
        reddit_api=check_key(settings.reddit_client_id) if settings.reddit_client_id else "❌ NOT SET",
        scraper_api=check_key(settings.scraper_api_key)
    )
