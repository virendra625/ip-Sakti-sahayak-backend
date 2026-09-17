"""Feedback API route for storing evaluation of answers and citations (Section 20)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.feedback import FeedbackCreate, FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Answer/Citation Feedback",
    description="Logs user evaluations (helpful, not_helpful, citation_wrong, answer_wrong, classification_wrong) for evaluation and continuous improvement.",
)
def submit_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    repo = ConversationRepository(db)
    fb = repo.add_feedback(
        rating=payload.rating,
        message_id=payload.message_id,
        comment=payload.comment,
    )
    return FeedbackResponse(
        feedback_id=fb.id,
        rating=fb.rating,
        message="Thank you! Feedback recorded successfully for system evaluation.",
    )
