"""
SQLAlchemy database models
"""
from sqlalchemy import Column, String, Integer, Float, JSON, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Search(Base):
    """
    Stores search queries and results
    """
    __tablename__ = "searches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artist = Column(String(255), nullable=False)
    song = Column(String(255), nullable=False)
    year = Column(Integer, nullable=True)
    search_hash = Column(String(64), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    # Relationship to gear results
    gear_results = relationship("GearResult", back_populates="search", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_artist_song', 'artist', 'song'),
    )


class GearResult(Base):
    """
    Stores synthesized gear information
    """
    __tablename__ = "gear_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_id = Column(UUID(as_uuid=True), ForeignKey('searches.id'), nullable=False)

    # Gear data (stored as JSON)
    guitars = Column(JSON)
    amps = Column(JSON)
    pedals = Column(JSON)
    signal_chain = Column(JSON)
    amp_settings = Column(JSON)
    context = Column(String)

    # Metadata
    confidence_score = Column(Float)
    sources = Column(JSON)  # Array of source information
    claude_response = Column(JSON)  # Full Claude response for debugging

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    search = relationship("Search", back_populates="gear_results")


class RawSourceData(Base):
    """
    Stores raw data from each source for debugging and reprocessing
    """
    __tablename__ = "raw_source_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    search_id = Column(UUID(as_uuid=True), ForeignKey('searches.id'), nullable=False)
    source_type = Column(String(50), nullable=False)  # 'reddit', 'youtube', 'equipboard', etc.
    raw_data = Column(JSON)
    fetched_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_search_source', 'search_id', 'source_type'),
    )
