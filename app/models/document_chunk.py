"""DocumentChunk model storing granular text snippets with structural metadata."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class DocumentChunk(Base):
    """Granular text chunk extracted from an authoritative document."""

    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_number = Column(String(100), nullable=True)  # e.g., "Section 3(p)", "Rule 153"
    heading = Column(String(255), nullable=True)  # e.g., "Non-patentable Inventions"
    chunk_index = Column(Integer, nullable=False, default=0)
    vector_id = Column(String(100), nullable=True, index=True)  # UUID or ID stored in Qdrant

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    document = relationship("Document", back_populates="chunks")
    citations = relationship("Citation", back_populates="chunk")

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} doc_id={self.document_id} sec='{self.section_number}'>"
