"""
Search endpoint
"""
from fastapi import APIRouter, HTTPException, status, Request
from uuid import uuid4
import hashlib
import logging
from datetime import datetime, timedelta

from src.api.models.requests import SearchRequest, PhotoSearchRequest
from src.api.models.responses import SearchResponse, GearResult
from src.services.aggregator import DataAggregator
from src.services.claude_service import ClaudeService
from src.services.vision_service import VisionService
from src.services.cache_manager import cache_manager
from src.middleware.rate_limiter import photo_rate_limiter
from src.database.connection import get_db_session
from src.database.models import Search, GearResult as DBGearResult, PhotoSearch
from sqlalchemy import select
import base64
import time

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
    logger.info(f"🔍 Search request: {request.artist} - {request.song} (year: {request.year})")

    # Generate search hash for caching
    search_hash = generate_search_hash(request.artist, request.song, request.year)
    search_id = uuid4()

    logger.info(f"🔑 Search ID: {search_id}, Hash: {search_hash}")

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

        # Log scraper results
        if scraper_results:
            logger.info(f"✓ Scrapers returned {len(scraper_results)} successful results")
            for result in scraper_results:
                logger.info(f"  - {result.source_name}: {len(str(result.data))} chars")
        else:
            logger.warning("⚠️ No scraper results - Claude will use pure inference from its knowledge")

        # Always synthesize with Claude (even with no scraper data, Claude can use its knowledge)
        claude_service = ClaudeService()
        gear_data = await claude_service.synthesize_gear_data(
            artist=request.artist,
            song=request.song,
            scraper_results=scraper_results,
            year=request.year
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


@router.post("/search/photo", response_model=SearchResponse, status_code=status.HTTP_200_OK)
async def search_gear_by_photo(body: PhotoSearchRequest, request: Request):
    """
    Identify gear from photo using Claude Vision

    Process:
    1. Decode and validate image
    2. Check cache by image hash
    3. Call VisionService for identification
    4. Cache result (90 days)
    5. Return SearchResponse
    """
    logger.info(f"📸 Photo search request (type hint: {body.gear_type}, context: {body.context})")

    # Check rate limit
    client_ip = request.client.host if request.client else "unknown"
    photo_rate_limiter.check_rate_limit(client_ip)

    start_time = time.time()
    search_id = uuid4()

    try:
        # Decode image
        try:
            image_data = base64.b64decode(body.image_data)
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid base64 image data"
            )

        # Generate hash for caching
        image_hash = hashlib.sha256(image_data).hexdigest()

        logger.info(f"🔑 Photo Search ID: {search_id}, Hash: {image_hash[:16]}...")

        # Check Redis cache first (fastest)
        cached_data = await cache_manager.get_photo_result(image_hash)
        if cached_data:
            logger.info(f"⚡ Redis cache hit for photo: {image_hash[:16]}...")
            processing_time = int((time.time() - start_time) * 1000)

            return SearchResponse(
                search_id=search_id,
                status='complete',
                artist=None,
                song=None,
                year=None,
                result=GearResult(**{
                    **cached_data,
                    'context': cached_data.get('context', '') + f" | Cached ({processing_time}ms)"
                })
            )

        # Check database cache
        async with get_db_session() as session:
            stmt = select(PhotoSearch).where(
                PhotoSearch.image_hash == image_hash,
                PhotoSearch.expires_at > datetime.utcnow()
            )
            result = await session.execute(stmt)
            existing_photo = result.scalar_one_or_none()

            if existing_photo:
                logger.info(f"✅ Cache hit for photo search: {image_hash[:16]}...")
                processing_time = int((time.time() - start_time) * 1000)

                return SearchResponse(
                    search_id=existing_photo.id,
                    status='complete',
                    artist=None,
                    song=None,
                    year=None,
                    result=GearResult(**{
                        'guitars': existing_photo.guitars or [],
                        'amps': existing_photo.amps or [],
                        'pedals': existing_photo.pedals or [],
                        'signal_chain': existing_photo.signal_chain or [],
                        'amp_settings': existing_photo.amp_settings,
                        'context': existing_photo.context or f"Photo analysis (cached, {processing_time}ms)",
                        'confidence_score': existing_photo.confidence_score or 0.0
                    })
                )

        # Cache miss - analyze with vision service
        logger.info("Cache miss - starting vision analysis")

        vision_service = VisionService()
        gear_data = await vision_service.identify_gear_from_image(
            image_data=image_data,
            gear_type=body.gear_type,
            context=body.context
        )

        processing_time = int((time.time() - start_time) * 1000)

        # Estimate cost (approximate: $0.015-0.022 per photo)
        # Using mid-range estimate of $0.019
        cost_usd = 0.019

        # Store in database
        async with get_db_session() as session:
            new_photo_search = PhotoSearch(
                id=search_id,
                image_hash=image_hash,
                expires_at=datetime.utcnow() + timedelta(days=90),
                guitars=gear_data.get('guitars', []),
                amps=gear_data.get('amps', []),
                pedals=gear_data.get('pedals', []),
                signal_chain=gear_data.get('signal_chain', []),
                amp_settings=gear_data.get('amp_settings'),
                context=gear_data.get('context'),
                confidence_score=gear_data.get('confidence_score', 0.0),
                gear_type_hint=body.gear_type,
                processing_time_ms=processing_time,
                cost_usd=cost_usd,
                reasoning=gear_data.get('reasoning')
            )
            session.add(new_photo_search)
            await session.commit()

        # Cache in Redis for fast retrieval
        await cache_manager.set_photo_result(image_hash, gear_data, ttl_days=90)

        logger.info(f"✅ Photo search complete: {search_id} ({processing_time}ms, ${cost_usd:.4f})")

        # Add processing metadata to context
        context = gear_data.get('context', '')
        if context:
            context += f" | Analysis time: {processing_time}ms"
        else:
            context = f"Photo analysis completed in {processing_time}ms"

        return SearchResponse(
            search_id=search_id,
            status='complete',
            artist=None,
            song=None,
            year=None,
            result=GearResult(**{
                **gear_data,
                'context': context
            })
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Validation errors (e.g., image too large)
        logger.error(f"Photo validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Photo search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Photo search failed: {str(e)}"
        )
