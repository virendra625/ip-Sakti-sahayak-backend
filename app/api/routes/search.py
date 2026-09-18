"""Search route for debugging and direct retrieval evaluation (Section 19)."""

from fastapi import APIRouter, status
from app.rag.retriever import get_retriever
from app.schemas.source import SearchRequest, SearchResponse
from app.utils.validators import normalize_jurisdiction

router = APIRouter(prefix="/search", tags=["Search & Debug"])


@router.post(
    "",
    response_model=SearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Direct Vector & Metadata Retrieval Search",
    description="Retrieves matching statutory chunks directly from Qdrant without invoking the LLM. Ideal for testing and evaluating retrieval accuracy.",
)
async def search_retrieval_endpoint(
    request: SearchRequest,
) -> SearchResponse:
    canonical_jurisdiction = normalize_jurisdiction(request.jurisdiction) or "India"
    retriever = get_retriever()
    results = await retriever.retrieve(
        query=request.query,
        jurisdiction=canonical_jurisdiction,
        topic=request.topic,
        document_type=request.document_type,
        limit=request.limit,
        score_threshold=request.score_threshold,
    )
    return SearchResponse(
        query=request.query,
        jurisdiction=canonical_jurisdiction,
        total_found=len(results),
        results=results,
    )
