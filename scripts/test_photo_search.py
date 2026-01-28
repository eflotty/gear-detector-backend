#!/usr/bin/env python3
"""
Test script for photo search functionality
"""
import asyncio
import base64
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.vision_service import VisionService
from src.database.connection import init_db, close_db
from src.services.cache_manager import cache_manager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_photo_search(image_path: str):
    """
    Test photo search with a sample image

    Args:
        image_path: Path to test image file
    """
    logger.info(f"Testing photo search with: {image_path}")

    try:
        # Initialize services
        await init_db()
        await cache_manager.connect()

        # Read image file
        with open(image_path, 'rb') as f:
            image_data = f.read()

        logger.info(f"📦 Image size: {len(image_data)} bytes")

        # Test vision service
        vision_service = VisionService()
        result = await vision_service.identify_gear_from_image(
            image_data=image_data,
            gear_type=None,
            context="test image"
        )

        # Print results
        logger.info("\n" + "="*50)
        logger.info("🎸 PHOTO SEARCH RESULTS")
        logger.info("="*50)
        logger.info(f"\nConfidence Score: {result.get('confidence_score', 0):.1f}%")
        logger.info(f"Context: {result.get('context', 'N/A')}")

        if result.get('guitars'):
            logger.info(f"\n🎸 Guitars Found: {len(result['guitars'])}")
            for guitar in result['guitars']:
                logger.info(f"  - {guitar.get('make')} {guitar.get('model')} (confidence: {guitar.get('confidence', 0):.1f}%)")

        if result.get('amps'):
            logger.info(f"\n🔊 Amps Found: {len(result['amps'])}")
            for amp in result['amps']:
                logger.info(f"  - {amp.get('make')} {amp.get('model')} (confidence: {amp.get('confidence', 0):.1f}%)")

        if result.get('pedals'):
            logger.info(f"\n🎛️ Pedals Found: {len(result['pedals'])}")
            for pedal in result['pedals']:
                logger.info(f"  - {pedal.get('make')} {pedal.get('model')} (confidence: {pedal.get('confidence', 0):.1f}%)")

        if result.get('reasoning'):
            reasoning = result['reasoning']
            logger.info(f"\n💭 Analysis Reasoning:")
            logger.info(f"  Visual Quality: {reasoning.get('visual_quality', 'N/A')}")
            logger.info(f"  Identification Basis: {reasoning.get('identification_basis', 'N/A')}")
            if reasoning.get('uncertainty_factors'):
                logger.info(f"  Uncertainty Factors: {reasoning.get('uncertainty_factors')}")

        logger.info("\n" + "="*50)
        logger.info("✅ Test completed successfully!")
        logger.info("="*50 + "\n")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        raise

    finally:
        await cache_manager.disconnect()
        await close_db()


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_photo_search.py <image_path>")
        print("\nExample:")
        print("  python test_photo_search.py /path/to/guitar.jpg")
        sys.exit(1)

    image_path = sys.argv[1]

    if not Path(image_path).exists():
        print(f"❌ Error: Image file not found: {image_path}")
        sys.exit(1)

    asyncio.run(test_photo_search(image_path))


if __name__ == "__main__":
    main()
