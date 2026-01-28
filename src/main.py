"""
ToneTrace API - Main Application Entry Point
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from contextlib import asynccontextmanager

from src.config import settings
from src.api.routes import health, search, analytics
from src.database.connection import init_db, close_db
from src.services.cache_manager import cache_manager
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting ToneTrace API...")
    await init_db()
    logger.info("Database initialized")

    await cache_manager.connect()
    logger.info("Cache manager initialized")

    yield

    # Shutdown
    logger.info("Shutting down ToneTrace API...")
    await cache_manager.disconnect()
    logger.info("Cache manager closed")

    await close_db()
    logger.info("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="ToneTrace API",
    description="API for identifying guitar gear used by artists in songs",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (allow iOS app to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your iOS app's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler to catch all unhandled errors
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["health"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "ToneTrace API",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info"
    )
