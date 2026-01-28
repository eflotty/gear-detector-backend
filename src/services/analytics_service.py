"""
Analytics service for tracking photo search metrics
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import PhotoSearch

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Track and analyze photo search metrics"""

    @staticmethod
    async def log_photo_search(
        session: AsyncSession,
        image_hash: str,
        confidence_score: float,
        processing_time_ms: int,
        cost_usd: float,
        gear_type_hint: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """
        Log photo search event for analytics

        Args:
            session: Database session
            image_hash: Hash of the analyzed image
            confidence_score: Confidence score of the result
            processing_time_ms: Processing time in milliseconds
            cost_usd: Estimated API cost
            gear_type_hint: Optional gear type hint provided
            success: Whether the search succeeded
            error: Error message if failed
        """
        logger.info(f"""
📊 Photo Search Analytics:
  - Hash: {image_hash[:16]}...
  - Confidence: {confidence_score:.1f}%
  - Processing Time: {processing_time_ms}ms
  - Cost: ${cost_usd:.4f}
  - Gear Type: {gear_type_hint or 'auto-detect'}
  - Success: {success}
  {f"- Error: {error}" if error else ""}
        """)

    @staticmethod
    async def get_photo_search_stats(
        session: AsyncSession,
        days: int = 7
    ) -> Dict:
        """
        Get photo search statistics for the past N days

        Args:
            session: Database session
            days: Number of days to analyze (default: 7)

        Returns:
            Dict with statistics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Total searches
        total_result = await session.execute(
            select(func.count(PhotoSearch.id))
            .where(PhotoSearch.created_at >= cutoff)
        )
        total_searches = total_result.scalar() or 0

        # Average confidence
        avg_confidence_result = await session.execute(
            select(func.avg(PhotoSearch.confidence_score))
            .where(PhotoSearch.created_at >= cutoff)
        )
        avg_confidence = avg_confidence_result.scalar() or 0.0

        # Average processing time
        avg_time_result = await session.execute(
            select(func.avg(PhotoSearch.processing_time_ms))
            .where(PhotoSearch.created_at >= cutoff)
        )
        avg_processing_time = avg_time_result.scalar() or 0.0

        # Total cost
        total_cost_result = await session.execute(
            select(func.sum(PhotoSearch.cost_usd))
            .where(PhotoSearch.created_at >= cutoff)
        )
        total_cost = total_cost_result.scalar() or 0.0

        # Gear type breakdown
        gear_type_result = await session.execute(
            select(
                PhotoSearch.gear_type_hint,
                func.count(PhotoSearch.id)
            )
            .where(PhotoSearch.created_at >= cutoff)
            .group_by(PhotoSearch.gear_type_hint)
        )
        gear_type_breakdown = {
            row[0] or "auto-detect": row[1]
            for row in gear_type_result.fetchall()
        }

        # Confidence distribution
        high_confidence = await session.execute(
            select(func.count(PhotoSearch.id))
            .where(
                PhotoSearch.created_at >= cutoff,
                PhotoSearch.confidence_score >= 80
            )
        )
        high_count = high_confidence.scalar() or 0

        medium_confidence = await session.execute(
            select(func.count(PhotoSearch.id))
            .where(
                PhotoSearch.created_at >= cutoff,
                PhotoSearch.confidence_score >= 50,
                PhotoSearch.confidence_score < 80
            )
        )
        medium_count = medium_confidence.scalar() or 0

        low_confidence = await session.execute(
            select(func.count(PhotoSearch.id))
            .where(
                PhotoSearch.created_at >= cutoff,
                PhotoSearch.confidence_score < 50
            )
        )
        low_count = low_confidence.scalar() or 0

        stats = {
            "period_days": days,
            "total_searches": total_searches,
            "average_confidence": round(avg_confidence, 2),
            "average_processing_time_ms": round(avg_processing_time, 0),
            "total_cost_usd": round(total_cost, 4),
            "cost_per_search": round(total_cost / total_searches, 4) if total_searches > 0 else 0,
            "gear_type_breakdown": gear_type_breakdown,
            "confidence_distribution": {
                "high (80-100%)": high_count,
                "medium (50-79%)": medium_count,
                "low (0-49%)": low_count
            },
            "success_rate": round((high_count + medium_count) / total_searches * 100, 1) if total_searches > 0 else 0
        }

        logger.info(f"""
📈 Photo Search Statistics ({days} days):
  - Total Searches: {stats['total_searches']}
  - Avg Confidence: {stats['average_confidence']}%
  - Avg Processing Time: {stats['average_processing_time_ms']}ms
  - Total Cost: ${stats['total_cost_usd']}
  - Success Rate: {stats['success_rate']}%
        """)

        return stats


# Global analytics service instance
analytics_service = AnalyticsService()
