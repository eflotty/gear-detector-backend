"""
API request models
"""
from pydantic import BaseModel, Field, validator
from typing import Optional
import base64


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


class PhotoSearchRequest(BaseModel):
    """Photo-based gear identification request"""
    image_data: str = Field(..., description="Base64 encoded image (JPEG/PNG)")
    gear_type: Optional[str] = Field(None, description="Optional hint: guitar, pedal, or amp")
    context: Optional[str] = Field(None, description="e.g., 'music video screenshot'")

    @validator('image_data')
    def validate_image_size(cls, v):
        """Ensure image is under 5MB when decoded"""
        try:
            data = base64.b64decode(v)
            if len(data) > 5 * 1024 * 1024:
                raise ValueError("Image must be under 5MB")
            return v
        except Exception as e:
            raise ValueError(f"Invalid base64 image data: {str(e)}")

    class Config:
        json_schema_extra = {
            "example": {
                "image_data": "base64_encoded_image_data_here...",
                "gear_type": "pedal",
                "context": "music video screenshot"
            }
        }
