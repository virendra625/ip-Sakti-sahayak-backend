"""Conversation session model for tracking dialogue history."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship

from app.db.database import Base


class Conversation(Base):
    """Dialogue session tracking user questions and grounded assistant replies."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(100), nullable=True, index=True)
    language = Column(String(10), nullable=False, default="en")
    jurisdiction = Column(String(100), nullable=False, default="India")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} lang={self.language} jurisdiction={self.jurisdiction}>"
