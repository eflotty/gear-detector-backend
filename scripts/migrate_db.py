#!/usr/bin/env python3
"""
Database migration script for ToneTrace
Creates all tables defined in models.py
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import init_db, close_db
from src.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run database migration"""
    logger.info(f"Connecting to database: {settings.database_url}")
    logger.info("Creating/updating tables...")

    try:
        await init_db()
        logger.info("✅ Database migration completed successfully!")
        logger.info("Tables created/updated:")
        logger.info("  - searches")
        logger.info("  - gear_results")
        logger.info("  - raw_source_data")
        logger.info("  - photo_searches (NEW)")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

    finally:
        await close_db()
        logger.info("Database connections closed")


if __name__ == "__main__":
    asyncio.run(main())
