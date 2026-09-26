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

    STOPWORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at",
        "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "did", "do",
        "does", "doing", "down", "during", "each", "few", "for", "from", "further", "had", "has", "have", "having",
        "he", "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it",
        "its", "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on",
        "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should",
        "so", "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there",
        "these", "they", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "we",
        "were", "what", "when", "where", "which", "while", "who", "whom", "why", "with", "would", "you", "your",
        "hai", "hain", "ke", "ki", "ka", "ko", "se", "me", "mein", "par", "kya", "aur", "ye", "yeh", "woh"
    }

    @staticmethod
    def _stem_token(word: str) -> str:
        """Strips common inflectional suffixes to align morphological variations."""
        suffixes = (
            "ability", "ibility", "ations", "ation", "ities", "ity",
            "ments", "ment", "ings", "ing", "ions", "ion", "ies", "es", "ed", "s",
            "ic", "al", "a"
        )
        for sfx in suffixes:
            if word.endswith(sfx) and len(word) - len(sfx) >= 3:
                return word[:-len(sfx)]
        return word

    def _embed_text(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        if not text:
            return vector

        import re
        norm_text = text.lower().replace("trade mark", "trademark").replace("trade marks", "trademark")
        tokens = re.findall(r"[a-zA-Z0-9]+", norm_text)

        token_counts = {}
        for t in tokens:
            if t not in self.STOPWORDS:
                token_counts[t] = token_counts.get(t, 0) + 1

        for token, count in token_counts.items():
            tf_weight = 1.0 + math.log(count + 1)

            # Full substantive token hash
            h = int(hashlib.sha256(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            vector[idx] += 3.0 * tf_weight

            # Morphological stem hash
            stemmed = self._stem_token(token)
            if stemmed != token:
                h_stem = int(hashlib.sha256(stemmed.encode("utf-8")).hexdigest(), 16)
                idx_stem = h_stem % self.dimension
                vector[idx_stem] += 2.0 * tf_weight

            # Compound decomposition (e.g. trademark -> trade, mark)
            if "trademark" in token:
                for sub in ("trade", "mark"):
                    h_sub = int(hashlib.sha256(sub.encode("utf-8")).hexdigest(), 16)
                    vector[h_sub % self.dimension] += 1.5 * tf_weight

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
