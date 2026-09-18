"""Qdrant vector store integration and hybrid retrieval engine."""

import uuid
from typing import Any, Dict, List, Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.core.logging import logger
from app.schemas.source import SearchResultChunk
from app.services.embedding_service import get_embedding_provider


class QdrantRetriever:
    """Manages vector collection lifecycle, chunk indexing, and hybrid filtered search."""

    def __init__(self):
        self.collection_name = settings.QDRANT_COLLECTION
        self.embedding_provider = get_embedding_provider()
        self.client = self._init_client()
        self._ensure_collection_exists()

    def _init_client(self) -> QdrantClient:
        """Connects to remote Qdrant service with seamless local fallback."""
        if settings.QDRANT_URL and not settings.QDRANT_URL.startswith("file"):
            try:
                client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                    timeout=3.0,
                )
                # Test connection
                client.get_collections()
                logger.info(f"Connected to Qdrant service at {settings.QDRANT_URL}")
                return client
            except Exception as exc:
                logger.warning(
                    f"Unable to connect to remote Qdrant ({settings.QDRANT_URL}): {exc}. "
                    f"Falling back to local embedded storage ({settings.QDRANT_LOCAL_PATH})."
                )

        # Embedded local directory mode
        return QdrantClient(path=settings.QDRANT_LOCAL_PATH)

    def _ensure_collection_exists(self) -> None:
        """Creates vector collection if it does not yet exist."""
        dim = self.embedding_provider.get_embedding_dimension()
        try:
            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)
            if not exists:
                logger.info(f"Creating Qdrant collection '{self.collection_name}' (dim={dim})...")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=dim,
                        distance=qmodels.Distance.COSINE,
                    ),
                )
        except Exception as exc:
            logger.error(f"Error checking/creating Qdrant collection: {exc}")

    async def upsert_chunks(self, chunks_metadata: List[Dict[str, Any]]) -> List[str]:
        """Generates embeddings and inserts/updates chunks into Qdrant."""
        if not chunks_metadata:
            return []

        texts = [c["chunk_text"] for c in chunks_metadata]
        embeddings = await self.embedding_provider.generate_batch_embeddings(texts)

        points = []
        point_ids = []
        for meta, vector in zip(chunks_metadata, embeddings):
            p_id = meta.get("vector_id") or str(uuid.uuid4())
            point_ids.append(p_id)

            payload = {
                "document_id": meta["document_id"],
                "document_title": meta["document_title"],
                "authority": meta.get("authority", "Official Authority"),
                "jurisdiction": meta.get("jurisdiction", "India"),
                "topic": meta.get("topic", "General"),
                "document_type": meta.get("document_type", "statute"),
                "version": meta.get("version", "current"),
                "section_number": meta.get("section_number"),
                "page_number": meta.get("page_number"),
                "heading": meta.get("heading"),
                "source_url": meta.get("source_url"),
                "chunk_text": meta["chunk_text"],
                "chunk_index": meta.get("chunk_index", 0),
            }

            points.append(
                qmodels.PointStruct(
                    id=p_id,
                    vector=vector,
                    payload=payload,
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info(f"Successfully upserted {len(points)} chunks into Qdrant.")
        return point_ids

    async def retrieve(
        self,
        query: str,
        jurisdiction: Optional[str] = "India",
        topic: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 5,
        score_threshold: Optional[float] = None,
    ) -> List[SearchResultChunk]:
        """Hybrid search executing semantic similarity with strict jurisdiction & topic filters."""
        query_vector = await self.embedding_provider.generate_embedding(query)

        # Build Qdrant filter conditions
        filter_conditions = []

        # 1. Jurisdiction filter (Strict isolation)
        if jurisdiction and jurisdiction.lower() != "all":
            filter_conditions.append(
                qmodels.FieldCondition(
                    key="jurisdiction",
                    match=qmodels.MatchValue(value=jurisdiction),
                )
            )

        # 2. Topic filter (optional)
        if topic and topic.lower() != "all":
            filter_conditions.append(
                qmodels.FieldCondition(
                    key="topic",
                    match=qmodels.MatchValue(value=topic),
                )
            )

        # 3. Document type filter (optional)
        if document_type and document_type.lower() != "all":
            filter_conditions.append(
                qmodels.FieldCondition(
                    key="document_type",
                    match=qmodels.MatchValue(value=document_type),
                )
            )

        q_filter = qmodels.Filter(must=filter_conditions) if filter_conditions else None

        # Execute vector search using configured similarity threshold
        effective_threshold = (
            score_threshold if score_threshold is not None else settings.SIMILARITY_THRESHOLD
        )

        try:
            hits = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=q_filter,
                limit=limit,
                score_threshold=effective_threshold,
            )
        except AttributeError:
            # Newer qdrant-client alternative
            res = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                query_filter=q_filter,
                limit=limit,
                score_threshold=effective_threshold,
            )
            hits = res.points

        results: List[SearchResultChunk] = []
        for hit in hits:
            score = round(float(hit.score), 4) if hasattr(hit, "score") and hit.score is not None else 0.0
            if effective_threshold is not None and score < effective_threshold:
                continue

            payload = hit.payload or {}
            results.append(
                SearchResultChunk(
                    document_id=payload.get("document_id", 0),
                    document_title=payload.get("document_title", "Unknown Document"),
                    authority=payload.get("authority", "Official Authority"),
                    jurisdiction=payload.get("jurisdiction", "India"),
                    topic=payload.get("topic", "General"),
                    section_number=payload.get("section_number"),
                    page_number=payload.get("page_number"),
                    heading=payload.get("heading"),
                    chunk_text=payload.get("chunk_text", ""),
                    relevance_score=score,
                    source_url=payload.get("source_url"),
                    version=payload.get("version", "current"),
                )
            )

        return results


# Global singleton instance
retriever_instance: Optional[QdrantRetriever] = None


def get_retriever() -> QdrantRetriever:
    """Singleton getter for retriever instance."""
    global retriever_instance
    if retriever_instance is None:
        retriever_instance = QdrantRetriever()
    return retriever_instance
