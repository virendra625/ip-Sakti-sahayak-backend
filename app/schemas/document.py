"""Pydantic schemas for Document and Chunk management."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DocumentBase(BaseModel):
    """Base document attributes."""
    title: str = Field(..., description="Official title of the legal/regulatory document")
    authority: str = Field(..., description="Issuing authority (e.g. Ministry of AYUSH, IPO)")
    jurisdiction: str = Field("India", description="Applicable jurisdiction (e.g. India, International)")
    country: str = Field("India", description="Country of origin")
    document_type: str = Field(..., description="Type (statute, regulation, guideline, treaty, etc.)")
    topic: str = Field(..., description="Domain topic (Patent, ASU_Medicine, Ayurveda_Aahar, etc.)")
    version: str = Field("current", description="Document version or amendment tag")
    publication_date: Optional[str] = Field(None, description="Official publication date")
    effective_date: Optional[str] = Field(None, description="Date when enforcement commenced")
    source_url: Optional[str] = Field(None, description="Official portal URL or reference link")
    language: str = Field("en", description="Language of text (en, hi)")
    description: Optional[str] = Field(None, description="Brief summary of document scope")


class DocumentCreate(DocumentBase):
    """Schema for registering a new document."""
    checksum: Optional[str] = Field(None, description="SHA-256 hash of content")


class DocumentChunkResponse(BaseModel):
    """Schema representing an extracted document chunk."""
    id: int
    document_id: int
    chunk_text: str
    page_number: Optional[int] = None
    section_number: Optional[str] = None
    heading: Optional[str] = None
    chunk_index: int
    vector_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(DocumentBase):
    """Schema for returning full document metadata."""
    id: int
    checksum: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    chunk_count: Optional[int] = Field(0, description="Total chunks indexed for this document")

    model_config = ConfigDict(from_attributes=True)


class DocumentIngestTextRequest(BaseModel):
    """Payload for ingesting raw legal text directly."""
    title: str = Field(..., examples=["The Patents Act, 1970 - Section 3(p)"])
    authority: str = Field(..., examples=["Indian Patent Office / Parliament of India"])
    jurisdiction: str = Field("India", examples=["India"])
    country: str = Field("India", examples=["India"])
    document_type: str = Field("statute", examples=["statute"])
    topic: str = Field("Patent", examples=["Patent"])
    version: str = Field("current", examples=["current"])
    text_content: str = Field(..., min_length=20, description="Full or extracted legal text content")
    source_url: Optional[str] = Field(None, examples=["https://ipindia.gov.in"])
    language: str = Field("en", examples=["en"])
    description: Optional[str] = Field(None, examples=["Section 3(p) regarding non-patentability of traditional knowledge."])


class DocumentIngestResponse(BaseModel):
    """Response returned upon successful document ingestion."""
    document_id: int
    title: str
    jurisdiction: str
    total_chunks: int
    checksum: str
    message: str
