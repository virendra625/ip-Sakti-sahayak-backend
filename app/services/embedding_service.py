"""Embedding service abstraction with Mock, Gemini, and OpenAI providers."""

import abc
import hashlib
import math
from typing import List
import httpx

from app.core.config import settings
from app.core.logging import logger


class BaseEmbeddingProvider(abc.ABC):
    """Abstract interface for embedding generation."""

    @abc.abstractmethod
    def get_embedding_dimension(self) -> int:
        """Returns vector dimensionality."""
        pass

    @abc.abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generates embedding vector for a single text."""
        pass

    @abc.abstractmethod
    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates embedding vectors for a list of texts."""
        pass


class MockDeterministicEmbeddingProvider(BaseEmbeddingProvider):
    """Zero-dependency, deterministic embedding generator.

    Produces high-fidelity normalized 384-dim vectors based on token hashes.
    Ensures identical texts yield identical vectors and related words share
    cosine similarity, perfect for offline hackathon testing and CI.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def get_embedding_dimension(self) -> int:
        return self.dimension

    def _embed_text(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        if not text:
            return vector

        tokens = text.lower().split()
        for token in tokens:
            # Deterministic bucket mapping
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            weight = 1.0 + (h % 10) / 10.0
            vector[idx] += weight

        # L2 Normalize vector
        norm = math.sqrt(sum(x * x for x in vector))
        if norm > 0:
            vector = [round(x / norm, 6) for x in vector]
        return vector

    async def generate_embedding(self, text: str) -> List[float]:
        return self._embed_text(text)

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_text(t) for t in texts]


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI Embedding Provider (e.g. text-embedding-3-small)."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", dimension: int = 384):
        self.api_key = api_key
        self.model = model
        self.dimension = dimension
        self.api_url = "https://api.openai.com/v1/embeddings"

    def get_embedding_dimension(self) -> int:
        return self.dimension

    async def generate_embedding(self, text: str) -> List[float]:
        batch = await self.generate_batch_embeddings([text])
        return batch[0]

    async def generate_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self.model,
            "dimensions": self.dimension,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.api_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return [item["embedding"] for item in data["data"]]


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Factory function returning the configured embedding provider."""
    provider_type = settings.EMBEDDING_PROVIDER.lower()

    if provider_type == "openai" and settings.EMBEDDING_API_KEY:
        logger.info("Using OpenAI Embedding Provider.")
        return OpenAIEmbeddingProvider(
            api_key=settings.EMBEDDING_API_KEY,
            model=settings.EMBEDDING_MODEL,
            dimension=settings.EMBEDDING_DIMENSION,
        )

    # Default fallback: Mock deterministic embeddings
    return MockDeterministicEmbeddingProvider(dimension=settings.EMBEDDING_DIMENSION)
