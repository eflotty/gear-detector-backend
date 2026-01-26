"""
API request models
"""
from pydantic import BaseModel, Field
from typing import Optional


class SearchRequest(BaseModel):
    """
    Search request body
    """
    artist: str = Field(..., min_length=1, max_length=255, description="Artist name")
    song: str = Field(..., min_length=1, max_length=255, description="Song title")
    year: Optional[int] = Field(None, ge=1900, le=2030, description="Optional year")

    class Config:
        json_schema_extra = {
            "example": {
                "artist": "Jimi Hendrix",
                "song": "Purple Haze",
                "year": 1967
            }
        }
