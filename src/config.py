"""
Configuration management using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables
    """
    # API Keys
    anthropic_api_key: str = ""
    reddit_client_id: Optional[str] = None
    reddit_client_secret: Optional[str] = None
    youtube_api_key: Optional[str] = None
    scraper_api_key: Optional[str] = None

    # Database
    database_url: str = "postgresql://eddieflottemesch@localhost:5432/geardetector"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # App Configuration
    environment: str = "development"
    log_level: str = "INFO"
    rate_limit_enabled: bool = True

    # Claude API Settings
    claude_model: str = "claude-3-5-sonnet-20241022"
    claude_max_tokens: int = 4000
    claude_timeout: int = 60

    # Scraping Settings
    scraper_timeout: int = 30
    scraper_max_concurrent: int = 5
    scraper_user_agent: str = "GearDetectorBot/1.0"

    # Cache Settings
    cache_ttl_seconds: int = 604800  # 7 days

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
