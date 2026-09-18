"""Schemas for conversational IPR and regulatory assistance."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.classification import ProductClassificationResponse
from app.schemas.source import SearchResultChunk


class CitationDetail(BaseModel):
    """Granular citation linked to an authoritative source chunk."""
    citation_id: int
    document_id: int
    document_title: str
    authority: str
    section: Optional[str] = None
    page: Optional[str] = None
    version: Optional[str] = None
    source_url: Optional[str] = None
    citation_text: str
    relevance_score: Optional[float] = None


class ConfidenceDetail(BaseModel):
    """Evidence confidence indicator."""
    level: str = Field(..., description="Evidence strength: HIGH, MEDIUM, LOW, or INSUFFICIENT")
    score: float = Field(..., ge=0.0, le=1.0, description="Calibrated score reflecting retrieval evidence density")
    reason: str = Field(..., description="Why this confidence level was assigned")


class ChatRequest(BaseModel):
    """Input payload for chat turn."""
    message: str = Field(..., min_length=2, examples=["Can an Ayurvedic classical formulation be patented in India?"])
    language: Optional[str] = Field(None, examples=["en"], description="Language code: 'en', 'hi', or 'hinglish' (auto-detected if omitted)")
    jurisdiction: Optional[str] = Field("India", examples=["India"], description="Selected jurisdiction (e.g. India, International)")
    conversation_id: Optional[str] = Field(None, examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"])
    product_context: Optional[Dict[str, Any]] = Field(
        None, description="Optional product formulation context to enrich retrieval & classification"
    )


class ChatResponse(BaseModel):
    """Comprehensive grounded assistant response with citations and safeguards."""
    conversation_id: str
    message_id: int
    answer: str
    language: str
    jurisdiction: str
    product_classification: Optional[ProductClassificationResponse] = None
    confidence: ConfidenceDetail
    citations: List[CitationDetail]
    sources: List[SearchResultChunk]
    missing_information: List[str] = Field(default_factory=list)
    conflict_detected: bool = False
    conflict_warning: Optional[str] = None
    disclaimer: str
