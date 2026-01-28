"""
Analytics endpoint for photo search metrics
"""
from fastapi import APIRouter, HTTPException, Query
import logging

from src.services.analytics_service import analytics_service
from src.services.cache_manager import cache_manager
from src.database.connection import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/analytics/photo-search")
async def get_photo_search_analytics(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to analyze")
):
    """
    Get photo search analytics and statistics

    Returns metrics including:
    - Total searches
    - Average confidence score
    - Processing time
    - Cost analysis
    - Success rate
    """
    try:
        async with get_db_session() as session:
            stats = await analytics_service.get_photo_search_stats(session, days=days)

        # Add cache stats
        cache_stats = await cache_manager.get_stats()

        return {
            "photo_search_stats": stats,
            "cache_stats": cache_stats,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Analytics error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve analytics: {str(e)}"
        )
