"""Feedback model for tracking user evaluations of answers, citations, and classifications."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from app.db.database import Base


class Feedback(Base):
    """User feedback on AI responses, citations, or classifications."""

    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True, index=True)
    rating = Column(String(50), nullable=False)  # helpful, not_helpful, citation_wrong, answer_wrong, classification_wrong
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} rating='{self.rating}'>"
