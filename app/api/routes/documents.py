"""Document management and ingestion routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.rag.ingestion import IngestionPipeline
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import (
    DocumentResponse,
    DocumentChunkResponse,
    DocumentIngestTextRequest,
    DocumentIngestResponse,
)

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/ingest",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Document Text",
    description="Ingests a raw legal or regulatory text, chunks it, stores in PostgreSQL, and generates Qdrant embeddings.",
)
async def ingest_document_text(
    payload: DocumentIngestTextRequest,
    db: Session = Depends(get_db),
) -> DocumentIngestResponse:
    pipeline = IngestionPipeline(db)
    result = await pipeline.ingest_raw_text(
        title=payload.title,
        text_content=payload.text_content,
        authority=payload.authority,
        jurisdiction=payload.jurisdiction,
        country=payload.country,
        document_type=payload.document_type,
        topic=payload.topic,
        version=payload.version,
        source_url=payload.source_url,
        language=payload.language,
        description=payload.description,
    )
    return result


@router.post(
    "/ingest/pdf",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest PDF Document",
    description="Uploads and parses a PDF document, extracting text per page and indexing it into PostgreSQL and Qdrant.",
)
async def ingest_document_pdf(
    file: UploadFile = File(...),
    title: str = Form(...),
    authority: str = Form(...),
    jurisdiction: str = Form("India"),
    country: str = Form("India"),
    document_type: str = Form("statute"),
    topic: str = Form("Patent"),
    version: str = Form("current"),
    source_url: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> DocumentIngestResponse:
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF document.",
        )

    pdf_bytes = await file.read()
    pipeline = IngestionPipeline(db)
    try:
        result = await pipeline.ingest_pdf_file(
            title=title,
            pdf_bytes=pdf_bytes,
            authority=authority,
            jurisdiction=jurisdiction,
            country=country,
            document_type=document_type,
            topic=topic,
            version=version,
            source_url=source_url,
            description=description,
        )
        return result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to process PDF: {str(exc)}",
        )


@router.get(
    "",
    response_model=List[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Authoritative Documents",
    description="Lists documents with optional filters for jurisdiction, topic, and document type.",
)
def list_documents(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction (e.g. India)"),
    topic: Optional[str] = Query(None, description="Filter by topic (e.g. Patent, ASU_Medicine)"),
    document_type: Optional[str] = Query(None, description="Filter by document type (e.g. statute)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[DocumentResponse]:
    doc_repo = DocumentRepository(db)
    docs, _ = doc_repo.list_documents(
        jurisdiction=jurisdiction,
        topic=topic,
        document_type=document_type,
        skip=skip,
        limit=limit,
    )
    result = []
    for d in docs:
        resp = DocumentResponse.model_validate(d)
        resp.chunk_count = len(d.chunks)
        result.append(resp)
    return result


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Document Details",
    description="Retrieves a specific document by its primary key identifier.",
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentResponse:
    doc_repo = DocumentRepository(db)
    doc = doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found.",
        )
    resp = DocumentResponse.model_validate(doc)
    resp.chunk_count = len(doc.chunks)
    return resp
