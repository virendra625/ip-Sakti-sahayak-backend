"""Document ingestion pipeline processing text/PDF, chunking, and dual-indexing."""

import hashlib
import io
import os
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.rag.chunking import chunk_document_by_sections_or_paragraphs, ChunkWithMetadata
from app.rag.retriever import get_retriever
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentIngestResponse


def compute_sha256(content: str) -> str:
    """Computes SHA-256 checksum of document text for version integrity."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> List[Dict[str, Any]]:
    """Extracts text per page from PDF bytes using pypdf (or PyMuPDF if available)."""
    pages_data = []

    # Attempt PyMuPDF (fitz) if installed
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text()
            if text.strip():
                pages_data.append({"page_number": page_idx + 1, "text": text})
        return pages_data
    except ImportError:
        pass

    # Fallback to pure-python pypdf
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        for page_idx, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages_data.append({"page_number": page_idx + 1, "text": text})
        return pages_data
    except Exception as exc:
        logger.error(f"Error parsing PDF with pypdf: {exc}")
        return []


class IngestionPipeline:
    """Orchestrates end-to-end ingestion: cleaning, chunking, DB persistence, and vector indexing."""

    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.retriever = get_retriever()

    async def ingest_raw_text(
        self,
        title: str,
        text_content: str,
        authority: str,
        jurisdiction: str = "India",
        country: str = "India",
        document_type: str = "statute",
        topic: str = "Patent",
        version: str = "current",
        source_url: Optional[str] = None,
        language: str = "en",
        description: Optional[str] = None,
        page_number: Optional[int] = 1,
    ) -> DocumentIngestResponse:
        """Ingests a raw text block into PostgreSQL and Qdrant."""
        checksum = compute_sha256(text_content)

        # Check for existing duplicate document by checksum
        existing_doc = self.doc_repo.get_by_checksum(checksum)
        if existing_doc:
            logger.info(f"Document '{title}' already exists with checksum {checksum[:8]}.")
            return DocumentIngestResponse(
                document_id=existing_doc.id,
                title=existing_doc.title,
                jurisdiction=existing_doc.jurisdiction,
                total_chunks=len(existing_doc.chunks),
                checksum=checksum,
                message="Document with identical content checksum already exists. Reused existing record.",
            )

        # 1. Create Document record in PostgreSQL
        doc_record = self.doc_repo.create(
            {
                "title": title,
                "authority": authority,
                "jurisdiction": jurisdiction,
                "country": country,
                "document_type": document_type,
                "topic": topic,
                "version": version,
                "source_url": source_url,
                "language": language,
                "description": description,
                "checksum": checksum,
            }
        )

        # 2. Chunk text with section detection
        chunks_meta: List[ChunkWithMetadata] = chunk_document_by_sections_or_paragraphs(
            full_text=text_content,
            page_number=page_number,
        )

        if not chunks_meta:
            logger.warning(f"No chunks generated for document '{title}'.")
            return DocumentIngestResponse(
                document_id=doc_record.id,
                title=doc_record.title,
                jurisdiction=doc_record.jurisdiction,
                total_chunks=0,
                checksum=checksum,
                message="Document registered, but no text content chunks could be extracted.",
            )

        # 3. Prepare chunk records for DB & Qdrant
        db_chunks_payload = []
        qdrant_chunks_payload = []

        import uuid
        for cm in chunks_meta:
            vec_id = str(uuid.uuid4())
            db_chunks_payload.append(
                {
                    "document_id": doc_record.id,
                    "chunk_text": cm.chunk_text,
                    "page_number": cm.page_number,
                    "section_number": cm.section_number,
                    "heading": cm.heading,
                    "chunk_index": cm.chunk_index,
                    "vector_id": vec_id,
                }
            )
            qdrant_chunks_payload.append(
                {
                    "document_id": doc_record.id,
                    "document_title": doc_record.title,
                    "authority": doc_record.authority,
                    "jurisdiction": doc_record.jurisdiction,
                    "topic": doc_record.topic,
                    "document_type": doc_record.document_type,
                    "version": doc_record.version,
                    "section_number": cm.section_number,
                    "page_number": cm.page_number,
                    "heading": cm.heading,
                    "source_url": doc_record.source_url,
                    "chunk_text": cm.chunk_text,
                    "chunk_index": cm.chunk_index,
                    "vector_id": vec_id,
                }
            )

        # Save to database
        saved_chunks = self.doc_repo.add_chunks(db_chunks_payload)

        # 4. Save to Qdrant vector index
        await self.retriever.upsert_chunks(qdrant_chunks_payload)

        logger.info(f"Ingested '{title}' with {len(saved_chunks)} chunks.")
        return DocumentIngestResponse(
            document_id=doc_record.id,
            title=doc_record.title,
            jurisdiction=doc_record.jurisdiction,
            total_chunks=len(saved_chunks),
            checksum=checksum,
            message="Document successfully processed, chunked, and dual-indexed in PostgreSQL & Qdrant.",
        )

    async def ingest_pdf_file(
        self,
        title: str,
        pdf_bytes: bytes,
        authority: str,
        jurisdiction: str = "India",
        country: str = "India",
        document_type: str = "statute",
        topic: str = "Patent",
        version: str = "current",
        source_url: Optional[str] = None,
        language: str = "en",
        description: Optional[str] = None,
    ) -> DocumentIngestResponse:
        """Ingests a multi-page PDF document."""
        pages = extract_text_from_pdf_bytes(pdf_bytes)
        if not pages:
            raise ValueError("Unable to extract any text from the provided PDF file.")

        full_text = "\n\n".join(p["text"] for p in pages)
        checksum = compute_sha256(full_text)

        existing_doc = self.doc_repo.get_by_checksum(checksum)
        if existing_doc:
            return DocumentIngestResponse(
                document_id=existing_doc.id,
                title=existing_doc.title,
                jurisdiction=existing_doc.jurisdiction,
                total_chunks=len(existing_doc.chunks),
                checksum=checksum,
                message="Document with identical PDF checksum already exists.",
            )

        doc_record = self.doc_repo.create(
            {
                "title": title,
                "authority": authority,
                "jurisdiction": jurisdiction,
                "country": country,
                "document_type": document_type,
                "topic": topic,
                "version": version,
                "source_url": source_url,
                "language": language,
                "description": description,
                "checksum": checksum,
            }
        )

        all_chunks: List[ChunkWithMetadata] = []
        global_chunk_idx = 0
        for p_info in pages:
            page_chunks = chunk_document_by_sections_or_paragraphs(
                full_text=p_info["text"],
                page_number=p_info["page_number"],
            )
            for c in page_chunks:
                c.chunk_index = global_chunk_idx
                global_chunk_idx += 1
                all_chunks.append(c)

        import uuid
        db_chunks_payload = []
        qdrant_chunks_payload = []

        for cm in all_chunks:
            vec_id = str(uuid.uuid4())
            db_chunks_payload.append(
                {
                    "document_id": doc_record.id,
                    "chunk_text": cm.chunk_text,
                    "page_number": cm.page_number,
                    "section_number": cm.section_number,
                    "heading": cm.heading,
                    "chunk_index": cm.chunk_index,
                    "vector_id": vec_id,
                }
            )
            qdrant_chunks_payload.append(
                {
                    "document_id": doc_record.id,
                    "document_title": doc_record.title,
                    "authority": doc_record.authority,
                    "jurisdiction": doc_record.jurisdiction,
                    "topic": doc_record.topic,
                    "document_type": doc_record.document_type,
                    "version": doc_record.version,
                    "section_number": cm.section_number,
                    "page_number": cm.page_number,
                    "heading": cm.heading,
                    "source_url": doc_record.source_url,
                    "chunk_text": cm.chunk_text,
                    "chunk_index": cm.chunk_index,
                    "vector_id": vec_id,
                }
            )

        saved = self.doc_repo.add_chunks(db_chunks_payload)
        await self.retriever.upsert_chunks(qdrant_chunks_payload)

        return DocumentIngestResponse(
            document_id=doc_record.id,
            title=doc_record.title,
            jurisdiction=doc_record.jurisdiction,
            total_chunks=len(saved),
            checksum=checksum,
            message="PDF successfully parsed, indexed by page/section, and stored in PostgreSQL & Qdrant.",
        )
