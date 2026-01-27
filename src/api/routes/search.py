"""
Search endpoint
"""
from fastapi import APIRouter, HTTPException, status
from uuid import uuid4
import hashlib
import logging
from datetime import datetime, timedelta

from src.api.models.requests import SearchRequest
from src.api.models.responses import SearchResponse, GearResult
from src.services.aggregator import DataAggregator
from src.services.claude_service import ClaudeService
from src.database.connection import get_db_session
from src.database.models import Search, GearResult as DBGearResult
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter()


def generate_search_hash(artist: str, song: str, year: int = None) -> str:
    """Generate unique hash for search query"""
    query_str = f"{artist.lower()}:{song.lower()}:{year or ''}"
    return hashlib.md5(query_str.encode()).hexdigest()


@router.post("/search", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search_gear(request: SearchRequest):
    """
    Search for guitar gear used by artist in a specific song

    Process:
    1. Check cache for existing results
    2. If not cached, aggregate data from all sources
    3. Use Claude AI to synthesize data
    4. Store results in database
    5. Return structured gear information
    """
    logger.info(f"Search request: {request.artist} - {request.song}")

    # Generate search hash for caching
    search_hash = generate_search_hash(request.artist, request.song, request.year)
    search_id = uuid4()

    try:
        # Check cache
        async with get_db_session() as session:
            # Look for existing recent search
            stmt = select(Search).where(
                Search.search_hash == search_hash,
                Search.expires_at > datetime.utcnow()
            )
            result = await session.execute(stmt)
            existing_search = result.scalar_one_or_none()

            if existing_search:
                logger.info(f"Cache hit for search: {search_hash}")

                # Fetch gear result
                gear_stmt = select(DBGearResult).where(
                    DBGearResult.search_id == existing_search.id
                )
                gear_result = await session.execute(gear_stmt)
                gear_data = gear_result.scalar_one_or_none()

                if gear_data:
                    return SearchResponse(
                        search_id=existing_search.id,
                        status='complete',
                        artist=request.artist,
                        song=request.song,
                        year=request.year,
                        result=GearResult(**{
                            'guitars': gear_data.guitars or [],
                            'amps': gear_data.amps or [],
                            'pedals': gear_data.pedals or [],
                            'signal_chain': gear_data.signal_chain or [],
                            'amp_settings': gear_data.amp_settings,
                            'context': gear_data.context,
                            'confidence_score': gear_data.confidence_score or 0.0
                        })
                    )

        # Cache miss - perform new search
        logger.info("Cache miss - starting new search")

        # Aggregate data from all sources
        aggregator = DataAggregator()
        scraper_results = await aggregator.aggregate(
            artist=request.artist,
            song=request.song,
            year=request.year
        )

        if not scraper_results:
            # Return mock data for testing when scrapers fail
            logger.warning("No scraper results, returning mock data for testing")
            gear_data = {
                "guitars": [
                    {
                        "make": "Fender",
                        "model": "Stratocaster",
                        "year": 1964,
                        "notes": "Iconic Strat used throughout Continuum era",
                        "confidence": 95.0,
                        "sources": ["Mock Data"]
                    },
                    {
                        "make": "PRS",
                        "model": "Super Eagle",
                        "year": None,
                        "notes": "Custom shop model frequently used in studio",
                        "confidence": 85.0,
                        "sources": ["Mock Data"]
                    }
                ],
                "amps": [
                    {
                        "make": "Dumble",
                        "model": "Overdrive Special",
                        "notes": "Legendary amp used for clean and overdrive tones",
                        "confidence": 90.0,
                        "sources": ["Mock Data"]
                    },
                    {
                        "make": "Two-Rock",
                        "model": "Custom Reverb",
                        "notes": "Main touring amp",
                        "confidence": 88.0,
                        "sources": ["Mock Data"]
                    }
                ],
                "pedals": [
                    {
                        "make": "Ibanez",
                        "model": "TS808 Tube Screamer",
                        "type": "Overdrive",
                        "confidence": 95.0,
                        "sources": ["Mock Data"]
                    },
                    {
                        "make": "Klon",
                        "model": "Centaur",
                        "type": "Overdrive",
                        "confidence": 92.0,
                        "sources": ["Mock Data"]
                    },
                    {
                        "make": "TC Electronic",
                        "model": "Flashback",
                        "type": "Delay",
                        "confidence": 80.0,
                        "sources": ["Mock Data"]
                    }
                ],
                "signal_chain": [
                    {"type": "guitar", "item": "Fender Stratocaster (1964)"},
                    {"type": "pedal", "item": "Ibanez TS808 Tube Screamer"},
                    {"type": "pedal", "item": "Klon Centaur"},
                    {"type": "pedal", "item": "TC Electronic Flashback"},
                    {"type": "amp", "item": "Dumble Overdrive Special"}
                ],
                "amp_settings": {
                    "gain": "Medium (5-6)",
                    "treble": "7",
                    "middle": "5",
                    "bass": "6",
                    "notes": "Clean headroom with slight breakup"
                },
                "context": f"This is mock data for testing purposes. Real gear data will be available once API keys are configured for {request.artist} - {request.song}.",
                "confidence_score": 85.0
            }
        else:
            # Synthesize with Claude when we have real data
            claude_service = ClaudeService()
            gear_data = await claude_service.synthesize_gear_data(
                artist=request.artist,
                song=request.song,
                scraper_results=scraper_results
            )

        # Store in database
        async with get_db_session() as session:
            # Create search record
            new_search = Search(
                id=search_id,
                artist=request.artist,
                song=request.song,
                year=request.year,
                search_hash=search_hash,
                expires_at=datetime.utcnow() + timedelta(days=90)
            )
            session.add(new_search)

            # Create gear result
            new_gear_result = DBGearResult(
                search_id=search_id,
                guitars=gear_data.get('guitars', []),
                amps=gear_data.get('amps', []),
                pedals=gear_data.get('pedals', []),
                signal_chain=gear_data.get('signal_chain', []),
                amp_settings=gear_data.get('amp_settings'),
                context=gear_data.get('context'),
                confidence_score=gear_data.get('confidence_score', 0.0),
                sources=[r.source_name for r in scraper_results],
                claude_response=gear_data
            )
            session.add(new_gear_result)

            await session.commit()

        logger.info(f"Search complete: {search_id}")

        return SearchResponse(
            search_id=search_id,
            status='complete',
            artist=request.artist,
            song=request.song,
            year=request.year,
            result=GearResult(**gear_data)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
