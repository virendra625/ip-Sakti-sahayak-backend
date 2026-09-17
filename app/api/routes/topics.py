"""Topics and metadata taxonomy route."""

from typing import Dict, List
from fastapi import APIRouter, status
from app.rag.metadata import get_metadata_taxonomy

router = APIRouter(prefix="/topics", tags=["Topics"])


@router.get(
    "",
    response_model=Dict[str, List[str]],
    status_code=status.HTTP_200_OK,
    summary="List IPR and Regulatory Topics",
    description="Returns the complete taxonomic list of domains, IPR topics, regulatory categories, and document types.",
)
def get_topics_taxonomy() -> Dict[str, List[str]]:
    return get_metadata_taxonomy()
