"""Repository for managing conversation history, messages, citations, and feedback."""

from typing import List, Optional
from sqlalchemy.orm import Session, joinedload

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.citation import Citation
from app.models.feedback import Feedback


class ConversationRepository:
    """Provides methods to persist conversations, chat turns, citations, and feedback."""

    def __init__(self, db: Session):
        self.db = db

    def get_or_create_conversation(
        self,
        conversation_id: Optional[str] = None,
        language: str = "en",
        jurisdiction: str = "India",
        session_id: Optional[str] = None,
    ) -> Conversation:
        """Retrieves an existing conversation by ID or creates a new one."""
        if conversation_id:
            conv = (
                self.db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if conv:
                return conv

        conv = Conversation(
            id=conversation_id if conversation_id else None,
            language=language,
            jurisdiction=jurisdiction,
            session_id=session_id,
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def add_message(self, conversation_id: str, role: str, content: str) -> Message:
        """Appends a message to the conversation."""
        msg = Message(conversation_id=conversation_id, role=role, content=content)
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def add_citations(self, message_id: int, citations_data: List[dict]) -> List[Citation]:
        """Attaches citations to an assistant message."""
        citations = []
        for c in citations_data:
            cit = Citation(
                message_id=message_id,
                document_id=c["document_id"],
                chunk_id=c.get("chunk_id"),
                citation_text=c["citation_text"],
                page_number=c.get("page_number"),
                section_number=c.get("section_number"),
                relevance_score=c.get("relevance_score"),
            )
            citations.append(cit)
        self.db.add_all(citations)
        self.db.commit()
        for cit in citations:
            self.db.refresh(cit)
        return citations

    def get_conversation_history(self, conversation_id: str, limit: int = 10) -> List[Message]:
        """Retrieves recent conversation messages with citations loaded."""
        return (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .options(joinedload(Message.citations))
            .order_by(Message.id.desc())
            .limit(limit)
            .all()[::-1]
        )

    def add_feedback(
        self, rating: str, message_id: Optional[int] = None, comment: Optional[str] = None
    ) -> Feedback:
        """Records user evaluation feedback."""
        fb = Feedback(rating=rating, message_id=message_id, comment=comment)
        self.db.add(fb)
        self.db.commit()
        self.db.refresh(fb)
        return fb
