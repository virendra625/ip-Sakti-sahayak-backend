"""Schemas for authoritative sources and search retrieval debugging."""

from typing import List, Optional
from pydantic import BaseModel, Field


class SourceItem(BaseModel):
    """Authoritative source metadata item."""
    id: int
    title: str
    authority: str
    jurisdiction: str
    document_type: str
    topic: str
    version: str
    source_url: Optional[str] = None
    description: Optional[str] = None


class SearchRequest(BaseModel):
    """Direct search request for testing and debugging retrieval."""
    query: str = Field(..., min_length=2, examples=["Can an Ayurvedic classical formulation be patented?"])
    jurisdiction: Optional[str] = Field("India", examples=["India"])
    topic: Optional[str] = Field(None, examples=["Patent"])
    document_type: Optional[str] = Field(None, examples=["statute"])
    limit: int = Field(5, ge=1, le=20, examples=[5])
    score_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Optional custom similarity threshold")


class SearchResultChunk(BaseModel):
    """Individual retrieved chunk with source attribution."""
    document_id: int
    document_title: str
    authority: str
    jurisdiction: str
    topic: str
    section_number: Optional[str] = None
    page_number: Optional[int] = None
    heading: Optional[str] = None
    chunk_text: str
    relevance_score: float
    source_url: Optional[str] = None
    version: str


class SearchResponse(BaseModel):
    """Direct search endpoint response."""
    query: str
    jurisdiction: str
    total_found: int
    results: List[SearchResultChunk]
