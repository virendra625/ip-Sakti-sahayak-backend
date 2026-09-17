"""Repository for accessing and querying documents and document chunks."""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class DocumentRepository:
    """Provides abstracted data-access methods for documents and chunks."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, document_id: int) -> Optional[Document]:
        """Retrieves a single document by primary key."""
        return self.db.query(Document).filter(Document.id == document_id).first()

    def get_by_checksum(self, checksum: str) -> Optional[Document]:
        """Checks if a document with identical content hash already exists."""
        return self.db.query(Document).filter(Document.checksum == checksum).first()

    def create(self, document_data: dict) -> Document:
        """Creates a new document record."""
        doc = Document(**document_data)
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def list_documents(
        self,
        jurisdiction: Optional[str] = None,
        topic: Optional[str] = None,
        document_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Document], int]:
        """Lists documents with optional filters and pagination."""
        query = self.db.query(Document)
        if jurisdiction and jurisdiction.lower() != "all":
            query = query.filter(func.lower(Document.jurisdiction) == jurisdiction.lower())
        if topic and topic.lower() != "all":
            query = query.filter(func.lower(Document.topic) == topic.lower())
        if document_type and document_type.lower() != "all":
            query = query.filter(func.lower(Document.document_type) == document_type.lower())

        total = query.count()
        docs = query.order_by(Document.id.desc()).offset(skip).limit(limit).all()
        return docs, total

    def add_chunks(self, chunks_data: List[dict]) -> List[DocumentChunk]:
        """Batch inserts document chunks."""
        chunks = [DocumentChunk(**chunk) for chunk in chunks_data]
        self.db.add_all(chunks)
        self.db.commit()
        for chunk in chunks:
            self.db.refresh(chunk)
        return chunks

    def get_chunk_by_id(self, chunk_id: int) -> Optional[DocumentChunk]:
        """Fetches a chunk by ID."""
        return self.db.query(DocumentChunk).filter(DocumentChunk.id == chunk_id).first()

    def get_chunks_by_ids(self, chunk_ids: List[int]) -> List[DocumentChunk]:
        """Fetches multiple chunks by primary key list."""
        return self.db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all()

    def get_distinct_jurisdictions(self) -> List[str]:
        """Returns distinct jurisdictions in the document repository."""
        rows = self.db.query(Document.jurisdiction).distinct().all()
        return [r[0] for r in rows if r[0]]

    def get_distinct_topics(self) -> List[str]:
        """Returns distinct topics present in the document repository."""
        rows = self.db.query(Document.topic).distinct().all()
        return [r[0] for r in rows if r[0]]

    def get_distinct_authorities(self) -> List[str]:
        """Returns distinct authorities present in the repository."""
        rows = self.db.query(Document.authority).distinct().all()
        return [r[0] for r in rows if r[0]]
