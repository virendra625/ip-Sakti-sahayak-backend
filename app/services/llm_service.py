"""Abstract LLM Service provider with Mock, Gemini, and OpenAI implementations."""

import abc
import os
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.schemas.source import SearchResultChunk


class BaseLLMProvider(abc.ABC):
    """Abstract interface for LLM text completion."""

    @abc.abstractmethod
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        retrieved_sources: List[SearchResultChunk],
        language: str = "en",
    ) -> str:
        """Generates an answer grounded strictly in retrieved sources."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """Grounded offline LLM simulator for testing and zero-cost local execution.

    Synthesizes accurate answers by extracting and structuring the exact statutory
    content found within the retrieved chunks, ensuring all citations [1], [2] are
    genuine and traceable to database records.
    """

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        retrieved_sources: List[SearchResultChunk],
        language: str = "en",
    ) -> str:
        if not retrieved_sources:
            if language == "hi":
                return (
                    "वर्तमान ज्ञानकोश में इस विषय पर आधिकारिक साक्ष्य उपलब्ध नहीं हैं। "
                    "कृपया किसी विधिक या विनियामक विशेषज्ञ से परामर्श लें।"
                )
            return (
                "I could not find sufficient authoritative evidence in the current knowledge base "
                "to answer this reliably. Please verify official statutory publications or consult a qualified legal professional."
            )

        # Build grounded synthesis based on top retrieved sources
        primary_chunk = retrieved_sources[0]
        sec_label = primary_chunk.section_number or "Statutory Provisions"
        doc_title = primary_chunk.document_title

        if language == "hi":
            response = (
                f"उपलब्ध आधिकारिक स्रोतों के आधार पर, {doc_title} के {sec_label} के अनुसार:\n\n"
            )
            for idx, src in enumerate(retrieved_sources[:3], start=1):
                clean_snippet = src.chunk_text.replace("\n", " ").strip()
                if len(clean_snippet) > 220:
                    clean_snippet = clean_snippet[:220] + "..."
                response += f"- {src.document_title} ({src.section_number or 'प्रावधान'}): {clean_snippet} [{idx}]\n\n"

            response += (
                "इस प्रकार, आयुर्वेद एवं पारंपरिक ज्ञान से संबंधित विनियामक तथा पेटेंट आवश्यकताओं "
                "का पालन करना अनिवार्य है। अधिक जानकारी के लिए संदर्भित स्रोतों का अवलोकन करें।"
            )
        else:
            response = (
                f"Based on the authoritative sources retrieved, under {doc_title} ({sec_label}):\n\n"
            )
            for idx, src in enumerate(retrieved_sources[:3], start=1):
                clean_snippet = src.chunk_text.replace("\n", " ").strip()
                if len(clean_snippet) > 220:
                    clean_snippet = clean_snippet[:220] + "..."
                response += f"• According to {src.document_title} ({src.section_number or 'Provisions'}): {clean_snippet} [{idx}]\n\n"

            response += (
                "Accordingly, any claims relating to Ayurvedic formulations, patentability exclusions, "
                "or regulatory compliance must be evaluated against these specific statutory requirements."
            )

        return response.strip()


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini LLM integration via REST API."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        )

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        retrieved_sources: List[SearchResultChunk],
        language: str = "en",
    ) -> str:
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": settings.LLM_TEMPERATURE,
                "maxOutputTokens": 1024,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"]
            return "Unable to generate a response from Gemini API."


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI Chat Completion provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        retrieved_sources: List[SearchResultChunk],
        language: str = "en",
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.LLM_TEMPERATURE,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


def get_llm_provider() -> BaseLLMProvider:
    """Factory creating the active LLM provider based on settings."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini" and settings.LLM_API_KEY:
        logger.info("Using Gemini LLM Provider.")
        return GeminiLLMProvider(api_key=settings.LLM_API_KEY, model=settings.GEMINI_MODEL)
    elif provider == "openai" and settings.LLM_API_KEY:
        logger.info("Using OpenAI LLM Provider.")
        return OpenAILLMProvider(api_key=settings.LLM_API_KEY, model=settings.OPENAI_MODEL)

    return MockLLMProvider()
