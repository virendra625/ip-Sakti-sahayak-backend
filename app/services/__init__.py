"""Services package with lazy attribute resolution to prevent eager dependency chain loading."""

from typing import Any

__all__ = [
    "BaseLLMProvider",
    "get_llm_provider",
    "BaseEmbeddingProvider",
    "get_embedding_provider",
    "RAGService",
    "ClassificationService",
    "CitationService",
    "EvidenceService",
    "TranslationService",
    "URLService",
]


def __getattr__(name: str) -> Any:
    """Lazily imports services upon first access so lightweight modules (like URLService)

    can be imported without initializing Qdrant or the RAG pipeline.
    """
    if name in ("BaseLLMProvider", "get_llm_provider"):
        from app.services.llm_service import BaseLLMProvider, get_llm_provider
        return BaseLLMProvider if name == "BaseLLMProvider" else get_llm_provider

    if name in ("BaseEmbeddingProvider", "get_embedding_provider"):
        from app.services.embedding_service import BaseEmbeddingProvider, get_embedding_provider
        return BaseEmbeddingProvider if name == "BaseEmbeddingProvider" else get_embedding_provider

    if name == "RAGService":
        from app.services.rag_service import RAGService
        return RAGService

    if name == "ClassificationService":
        from app.services.classification_service import ClassificationService
        return ClassificationService

    if name == "CitationService":
        from app.services.citation_service import CitationService
        return CitationService

    if name == "EvidenceService":
        from app.services.evidence_service import EvidenceService
        return EvidenceService

    if name == "TranslationService":
        from app.services.translation_service import TranslationService
        return TranslationService

    if name == "URLService":
        from app.services.url_service import URLService
        return URLService

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
