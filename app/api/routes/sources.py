"""Authoritative sources route."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.document_repository import DocumentRepository
from app.schemas.source import SourceItem

router = APIRouter(prefix="/sources", tags=["Sources"])


@router.get(
    "",
    response_model=List[SourceItem],
    status_code=status.HTTP_200_OK,
    summary="List Authoritative Sources",
    description="Returns metadata of authoritative statutes, regulations, and pharmacopoeial guidelines currently indexed in the knowledge base.",
)
def list_sources(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    db: Session = Depends(get_db),
) -> List[SourceItem]:
    repo = DocumentRepository(db)
    docs, _ = repo.list_documents(jurisdiction=jurisdiction, topic=topic, limit=100)
    return [
        SourceItem(
            id=d.id,
            title=d.title,
            authority=d.authority,
            jurisdiction=d.jurisdiction,
            document_type=d.document_type,
            topic=d.topic,
            version=d.version,
            source_url=d.source_url,
            description=d.description,
        )
        for d in docs
    ]
