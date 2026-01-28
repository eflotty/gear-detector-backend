"""
API response models
"""
from pydantic import BaseModel
from typing import List, Optional, Dict
from uuid import UUID


class GuitarInfo(BaseModel):
    make: str
    model: str
    year: Optional[int] = None
    notes: Optional[str] = None
    confidence: float
    sources: List[str]


class AmpInfo(BaseModel):
    make: str
    model: str
    notes: Optional[str] = None
    confidence: float
    sources: List[str]


class PedalInfo(BaseModel):
    make: str
    model: str
    type: Optional[str] = None
    confidence: float
    sources: List[str]


class SignalChainItem(BaseModel):
    type: str  # 'guitar', 'pedal', 'amp'
    item: str


class AmpSettings(BaseModel):
    gain: Optional[str] = None
    treble: Optional[str] = None
    middle: Optional[str] = None
    bass: Optional[str] = None
    notes: Optional[str] = None


class GearResult(BaseModel):
    guitars: List[GuitarInfo]
    amps: List[AmpInfo]
    pedals: List[PedalInfo]
    signal_chain: List[SignalChainItem]
    amp_settings: Optional[AmpSettings] = None
    context: Optional[str] = None
    confidence_score: float
    conflicts: Optional[List[Dict[str, str]]] = None
    notes: Optional[str] = None


class SearchResponse(BaseModel):
    search_id: UUID
    status: str  # 'processing', 'complete', 'error'
    artist: Optional[str] = None  # Optional for photo searches
    song: Optional[str] = None  # Optional for photo searches
    year: Optional[int] = None
    result: Optional[GearResult] = None
    error: Optional[str] = None
