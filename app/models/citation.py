"""Citation model linking assistant statements directly to authoritative source chunks."""

from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base


class Citation(Base):
    """Authoritative citation mapping assistant claims to documents and chunks."""

    __tablename__ = "citations"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True, index=True)
    citation_text = Column(Text, nullable=False)
    page_number = Column(Integer, nullable=True)
    section_number = Column(String(100), nullable=True)
    relevance_score = Column(Float, nullable=True)

    # Relationships
    message = relationship("Message", back_populates="citations")
    document = relationship("Document", back_populates="citations")
    chunk = relationship("DocumentChunk", back_populates="citations")

    def __repr__(self) -> str:
        return f"<Citation id={self.id} msg_id={self.message_id} doc_id={self.document_id}>"
