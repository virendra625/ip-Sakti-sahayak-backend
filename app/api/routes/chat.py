"""Chat API route providing source-cited, grounded conversational IPR guidance."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag_service import RAGService
from app.core.security import sanitize_input_text, validate_no_injection_patterns

router = APIRouter(prefix="/chat", tags=["Chat & RAG"])


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask Question with Source Citations",
    description=(
        "Processes an IPR or regulatory question regarding Ayurvedic products. "
        "Performs hybrid retrieval from Qdrant, synthesizes a grounded answer using the configured LLM, "
        "validates evidence, generates precise citations, and logs conversation history."
    ),
)
async def chat_endpoint(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    # 1. Input sanitization & security checks
    sanitized_message = sanitize_input_text(request.message)
    if not validate_no_injection_patterns(sanitized_message):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The provided message contains invalid or potentially unsafe characters.",
        )
    request.message = sanitized_message

    # 2. Manage Conversation & Message persistence
    conv_repo = ConversationRepository(db)
    conv = conv_repo.get_or_create_conversation(
        conversation_id=request.conversation_id,
        language=request.language or "en",
        jurisdiction=request.jurisdiction or "India",
    )
    request.conversation_id = conv.id

    # Record User Message
    user_msg = conv_repo.add_message(
        conversation_id=conv.id,
        role="user",
        content=request.message,
    )

    # 3. Execute Grounded RAG Pipeline
    rag_service = RAGService(db)
    response: ChatResponse = await rag_service.answer_question(request)

    # 4. Record Assistant Message & Attached Citations in DB
    asst_msg = conv_repo.add_message(
        conversation_id=conv.id,
        role="assistant",
        content=response.answer,
    )
    response.message_id = asst_msg.id
    response.conversation_id = conv.id

    if response.citations:
        citations_payload = []
        for c in response.citations:
            citations_payload.append(
                {
                    "document_id": c.document_id,
                    "citation_text": c.citation_text,
                    "page_number": int(c.page) if c.page and c.page.isdigit() else None,
                    "section_number": c.section,
                    "relevance_score": c.relevance_score,
                }
            )
        conv_repo.add_citations(asst_msg.id, citations_payload)

    return response
