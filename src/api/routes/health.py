"""
Health check endpoint
"""
from fastapi import APIRouter, status
from pydantic import BaseModel
import redis.asyncio as redis
from sqlalchemy import text

from src.config import settings
from src.database.connection import get_db_session
from src.services.aggregator import DataAggregator

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


@router.get("/test-scrapers")
async def test_scrapers():
    """
    Test all scrapers with a known artist to verify they're working

    This is a diagnostic endpoint - uses "John Mayer" as test artist
    Returns detailed results from each scraper
    """
    aggregator = DataAggregator()

    # Test with a well-known artist
    results = await aggregator.aggregate(
        artist="John Mayer",
        song="Gravity",
        year=2006
    )

    # Format results for display
    scraper_status = []
    for result in results:
        scraper_status.append({
            "source": result.source_name,
            "success": result.success,
            "confidence": result.confidence,
            "error": result.error,
            "data_size": len(str(result.data)) if result.data else 0,
            "has_data": bool(result.data)
        })

    # Also check scrapers that failed
    all_scrapers = [s.__class__.__name__.replace('Scraper', '').lower() for s in aggregator.scrapers]
    successful_scrapers = [r.source_name for r in results if r.success]
    failed_scrapers = [s for s in all_scrapers if s not in successful_scrapers]

    return {
        "test_query": "John Mayer - Gravity (2006)",
        "total_scrapers": len(all_scrapers),
        "successful": len(successful_scrapers),
        "failed": len(failed_scrapers),
        "scraper_details": scraper_status,
        "successful_scrapers": successful_scrapers,
        "failed_scrapers": failed_scrapers
    }


@router.get("/test-claude")
async def test_claude():
    """
    Test Claude API connection and try different model names
    """
    from anthropic import AsyncAnthropic

    if not settings.anthropic_api_key:
        return {"error": "ANTHROPIC_API_KEY not set"}

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Try different model names
    models_to_test = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-sonnet-20240229",
        "claude-3-opus-20240229"
    ]

    results = {}

    for model in models_to_test:
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            results[model] = "✅ WORKS"
        except Exception as e:
            results[model] = f"❌ {str(e)[:100]}"

    return {
        "current_setting": settings.claude_model,
        "api_key_preview": settings.anthropic_api_key[:15] + "..." if settings.anthropic_api_key else None,
        "model_tests": results
    }


@router.get("/clear-cache")
async def clear_cache():
    """
    Clear all cached search results from the database

    DANGER: This deletes all cached searches. Use only for development/debugging.
    Can be called via browser GET request for easy access.
    """
    from src.database.connection import get_db_session
    from src.database.models import Search, GearResult
    from sqlalchemy import delete

    async with get_db_session() as session:
        # Delete all gear results first (foreign key constraint)
        await session.execute(delete(GearResult))

        # Delete all searches
        await session.execute(delete(Search))

        await session.commit()

    return {
        "status": "success",
        "message": "All cached searches cleared",
        "note": "Next searches will run scrapers and Claude synthesis from scratch"
    }
