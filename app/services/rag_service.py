"""RAG Orchestration Service coordinating retrieval, grounding, citation, and safety guardrails."""

import time
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.rag.prompt_templates import (
    SYSTEM_PROMPT_EN,
    SYSTEM_PROMPT_HI,
    USER_PROMPT_TEMPLATE,
)
from app.schemas.chat import ChatRequest, ChatResponse, CitationDetail
from app.schemas.classification import ProductClassificationRequest, ProductClassificationResponse
from app.schemas.source import SearchResultChunk
from app.services.classification_service import ClassificationService
from app.services.citation_service import CitationService
from app.services.evidence_service import EvidenceService
from app.services.llm_service import get_llm_provider
from app.services.translation_service import TranslationService
from app.utils.language import detect_language
from app.utils.validators import normalize_jurisdiction


class RAGService:
    """Orchestrates the entire question-answering workflow."""

    def __init__(self, db: Session):
        self.db = db
        from app.rag.retriever import get_retriever
        self.retriever = get_retriever()
        self.llm_provider = get_llm_provider()

    async def answer_question(self, request: ChatRequest) -> ChatResponse:
        start_time = time.time()

        # 1. Language Detection & Query Translation Preprocessing
        detected_lang = request.language or detect_language(request.message)
        processed_query = TranslationService.prepare_retrieval_query(
            request.message, detected_lang
        )

        # 2. Jurisdiction Resolution & Check (Section 16)
        raw_jurisdiction = request.jurisdiction
        canonical_jurisdiction = normalize_jurisdiction(raw_jurisdiction) or "India"

        # Check for open patentability question without specified jurisdiction
        if not raw_jurisdiction and ("patent" in request.message.lower() or "पेटेंट" in request.message):
            return ChatResponse(
                conversation_id=request.conversation_id or "new_session",
                message_id=0,
                answer=(
                    "Which jurisdiction should I analyse? Patent laws and traditional knowledge protections "
                    "differ significantly between India (e.g. Section 3(p) of the Patents Act) and foreign jurisdictions."
                    if detected_lang == "en"
                    else "आप किस क्षेत्राधिकार (Jurisdiction) का विश्लेषण करना चाहते हैं? कृपया भारत (India) या अंतर्राष्ट्रीय (International) निर्दिष्ट करें।"
                ),
                language=detected_lang,
                jurisdiction="Unspecified",
                product_classification=None,
                confidence={
                    "level": "INSUFFICIENT",
                    "score": 0.0,
                    "reason": "Jurisdiction is required to provide accurate legal guidance.",
                },
                citations=[],
                sources=[],
                missing_information=["Please specify the target jurisdiction (e.g. India, International)."],
                disclaimer=TranslationService.get_localized_disclaimer(detected_lang),
            )

        # 3. Product Classification (if product context provided)
        classification_result: Optional[ProductClassificationResponse] = None
        filter_topic: Optional[str] = None

        if request.product_context:
            try:
                class_req = ProductClassificationRequest(**request.product_context)
                classification_result = ClassificationService.classify_product(class_req)
                if classification_result.relevant_topics:
                    filter_topic = classification_result.relevant_topics[0]
            except Exception as exc:
                logger.warning(f"Could not parse product_context for classification: {exc}")

        # 4. Hybrid Vector Retrieval
        retrieval_start = time.time()
        retrieved_sources: List[SearchResultChunk] = await self.retriever.retrieve(
            query=processed_query,
            jurisdiction=canonical_jurisdiction,
            topic=filter_topic,
            limit=5,
        )
        retrieval_duration = round((time.time() - retrieval_start) * 1000, 2)
        logger.info(
            f"RAG Retrieval completed in {retrieval_duration}ms - Retrieved {len(retrieved_sources)} chunks."
        )

        # 5. Format Retrieved Context & Assemble Prompt
        sources_block = ""
        if retrieved_sources:
            for idx, src in enumerate(retrieved_sources, start=1):
                sec = f" | Section: {src.section_number}" if src.section_number else ""
                pg = f" | Page: {src.page_number}" if src.page_number else ""
                sources_block += (
                    f"[{idx}] {src.document_title} (Authority: {src.authority}{sec}{pg})\n"
                    f"Content: {src.chunk_text}\n\n"
                )
        else:
            sources_block = "NO RELEVANT SOURCES RETRIEVED."

        product_block = "None"
        if classification_result:
            product_block = (
                f"Likely Category: {classification_result.likely_category}\n"
                f"Reasoning: {classification_result.reasoning_summary}\n"
                f"IPR Guidance: {', '.join(classification_result.ipr_implications)}"
            )

        system_prompt = (
            SYSTEM_PROMPT_HI.format(jurisdiction=canonical_jurisdiction)
            if detected_lang == "hi"
            else SYSTEM_PROMPT_EN.format(jurisdiction=canonical_jurisdiction)
        )

        user_prompt = USER_PROMPT_TEMPLATE.format(
            retrieved_sources_block=sources_block,
            product_context_block=product_block,
            user_query=request.message,
        )

        # 6. Generate Response via LLM
        llm_start = time.time()
        raw_answer = await self.llm_provider.generate_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            retrieved_sources=retrieved_sources,
            language=detected_lang,
        )
        llm_duration = round((time.time() - llm_start) * 1000, 2)
        logger.info(f"LLM generation completed in {llm_duration}ms.")

        # 7. Extract and Map Citations (Section 13)
        citations: List[CitationDetail] = CitationService.extract_and_build_citations(
            answer_text=raw_answer,
            retrieved_sources=retrieved_sources,
        )

        # 8. Evidence Validation & Conflict Detection (Section 14 & 15)
        confidence_detail, conflict_detected, conflict_warning = EvidenceService.validate_and_score_evidence(
            retrieved_sources=retrieved_sources,
            citations=citations,
            selected_jurisdiction=canonical_jurisdiction,
        )

        # 9. Handle Insufficient Evidence Safeguard (Section 15)
        if confidence_detail.level == "INSUFFICIENT" or not retrieved_sources:
            if detected_lang == "hi":
                raw_answer = (
                    "वर्तमान ज्ञानकोश में इस विषय पर आधिकारिक साक्ष्य उपलब्ध नहीं हैं। "
                    "मैं बिना आधिकारिक स्रोत के अनुमानित उत्तर नहीं दे सकता।"
                )
            else:
                raw_answer = (
                    "I could not find sufficient authoritative evidence in the current knowledge base to answer this reliably. "
                    "The system does not fabricate legal conclusions when authoritative sources are missing."
                )

        disclaimer = TranslationService.get_localized_disclaimer(detected_lang)

        return ChatResponse(
            conversation_id=request.conversation_id or "demo_session",
            message_id=1,
            answer=raw_answer,
            language=detected_lang,
            jurisdiction=canonical_jurisdiction,
            product_classification=classification_result,
            confidence=confidence_detail,
            citations=citations,
            sources=retrieved_sources,
            missing_information=(
                classification_result.missing_information if classification_result else []
            ),
            conflict_detected=conflict_detected,
            conflict_warning=conflict_warning,
            disclaimer=disclaimer,
        )
