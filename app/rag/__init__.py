"""RAG pipeline package."""

from app.rag.retriever import QdrantRetriever, get_retriever
from app.rag.ingestion import IngestionPipeline
from app.rag.chunking import chunk_document_by_sections_or_paragraphs
from app.rag.metadata import DOMAINS, IPR_TOPICS, REGULATORY_TOPICS, DOCUMENT_TYPES

__all__ = [
    "QdrantRetriever",
    "get_retriever",
    "IngestionPipeline",
    "chunk_document_by_sections_or_paragraphs",
    "DOMAINS",
    "IPR_TOPICS",
    "REGULATORY_TOPICS",
    "DOCUMENT_TYPES",
]
