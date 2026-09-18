"""Citation extraction, verification, and formatting service."""

import re
from typing import List, Tuple
from app.schemas.chat import CitationDetail
from app.schemas.source import SearchResultChunk


class CitationService:
    """Handles mapping of bracket citations [1], [2] to actual retrieved chunks

    and formats authoritative citations without hallucinated sections or pages.
    """

    @staticmethod
    def extract_and_build_citations(
        answer_text: str, retrieved_sources: List[SearchResultChunk]
    ) -> List[CitationDetail]:
        """Scans generated text for citation markers [1], [2], matches them against

        retrieved chunks, and constructs structured CitationDetail objects.
        """
        # Find all brackets containing integers: e.g. [1], [2], [1, 2], [Source 1], [source 2]
        matches = re.findall(r"\[(?:Source\s*)?([0-9]+(?:\s*,\s*[0-9]+)*)\]", answer_text, re.IGNORECASE)
        cited_indices = set()
        for m in matches:
            for part in m.split(","):
                part = part.strip()
                if part.isdigit():
                    cited_indices.add(int(part))

        # NOTE: Do NOT fallback to {1} if cited_indices is empty.
        # Showing Source 1 when it was not cited leads to hallucinated attribution.

        citations: List[CitationDetail] = []
        for idx in sorted(list(cited_indices)):
            # 1-indexed mapping to retrieved_sources
            chunk_idx = idx - 1
            if 0 <= chunk_idx < len(retrieved_sources):
                src = retrieved_sources[chunk_idx]

                section_str = src.section_number
                if not section_str:
                    section_str = "Section/page information unavailable in retrieved source."

                page_str = str(src.page_number) if src.page_number else "Page information unavailable in retrieved source."

                formatted_citation_text = (
                    f"[{idx}] {src.document_title}\n"
                    f"Authority: {src.authority}\n"
                    f"Section: {section_str}\n"
                    f"Page: {page_str}\n"
                    f"Version: {src.version}\n"
                    f"Source: {src.source_url or 'Official Government Record'}"
                )

                citations.append(
                    CitationDetail(
                        citation_id=idx,
                        document_id=src.document_id,
                        document_title=src.document_title,
                        authority=src.authority,
                        section=section_str,
                        page=page_str,
                        version=src.version,
                        source_url=src.source_url,
                        citation_text=formatted_citation_text,
                        relevance_score=src.relevance_score,
                    )
                )

        return citations
