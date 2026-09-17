"""Document model storing legal and regulatory source metadata."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship

from app.db.database import Base


class Document(Base):
    """Authoritative legal, regulatory, or pharmacopoeial document."""

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    authority = Column(String(255), nullable=False, index=True)  # e.g., "Ministry of AYUSH", "IPO", "FSSAI"
    jurisdiction = Column(String(100), nullable=False, default="India", index=True)  # "India", "International"
    country = Column(String(100), nullable=False, default="India")
    document_type = Column(String(100), nullable=False, index=True)  # statute, regulation, guideline, etc.
    topic = Column(String(100), nullable=False, index=True)  # Patent, ASU_Medicine, Ayurveda_Aahar, etc.
    version = Column(String(50), nullable=False, default="current")
    publication_date = Column(String(50), nullable=True)
    effective_date = Column(String(50), nullable=True)
    source_url = Column(String(1000), nullable=True)
    language = Column(String(10), nullable=False, default="en")
    description = Column(Text, nullable=True)
    checksum = Column(String(64), nullable=True)  # SHA-256 hash for version tracking

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    citations = relationship("Citation", back_populates="document")

    def __repr__(self) -> str:
        return f"<Document id={self.id} title='{self.title[:30]}' jurisdiction='{self.jurisdiction}'>"
