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
