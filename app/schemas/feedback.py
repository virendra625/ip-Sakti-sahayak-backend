"""Schemas for feedback submission and logging."""

from typing import Optional
from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """User feedback submission payload."""
    message_id: Optional[int] = Field(None, description="Optional ID of the message being evaluated")
    rating: str = Field(
        ...,
        pattern="^(helpful|not_helpful|citation_wrong|answer_wrong|classification_wrong)$",
        examples=["helpful"],
        description="Rating category: helpful, not_helpful, citation_wrong, answer_wrong, classification_wrong"
    )
    comment: Optional[str] = Field(None, max_length=1000, examples=["Accurately cited Section 3(p) of the Patents Act."])


class FeedbackResponse(BaseModel):
    """Feedback confirmation response."""
    feedback_id: int
    rating: str
    message: str
