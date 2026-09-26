"""Citation extraction, claim-level verification, and formatting service."""

import re
from typing import List, Optional
from app.schemas.chat import CitationDetail
from app.schemas.source import SearchResultChunk


class CitationService:
    """Handles mapping of bracket citations [1], [2], [Source 1] to actual retrieved chunks,

    verifies claim-level topical and statutory grounding, and formats authoritative citations.
    """

    @classmethod
    def get_enclosing_claim(cls, text: str, match_start: int, match_end: int) -> str:
        """Extracts the sentence or bullet clause directly preceding or enclosing the citation bracket."""
        preceding = text[:match_start]
        start_idx = 0
        for sep in ("\n", "•", ".\n", "  "):
            pos = preceding.rfind(sep)
            if pos != -1 and (pos + len(sep)) > start_idx:
                start_idx = pos + len(sep)

        following = text[match_end:]
        end_idx = len(text)
        for sep in ("\n", "•", ".\n"):
            pos = following.find(sep)
            if pos != -1 and (match_end + pos) < end_idx:
                end_idx = match_end + pos

        claim = text[start_idx:end_idx].strip()
        # If claim extracted is too short (just bracket), grab preceding sentence
        if len(claim) <= (match_end - match_start + 4):
            claim = text[max(0, match_start - 250):end_idx].strip()
        return claim

    @classmethod
    def is_claim_supported_by_source(cls, claim_text: str, source: SearchResultChunk) -> bool:
        """Evaluates whether a specific sentence/claim containing a citation is topically

        and legally compatible with the referenced source.
        """
        claim_lower = claim_text.lower()
        src_topic = (source.topic or "").lower()
        src_title = (source.document_title or "").lower()

        # 1. Trademark claim citing Patent, Biodiversity, or Food source
        has_tm_claim = any(k in claim_lower for k in ("trademark", "trade mark", "brand name", "logo", "nice class", "class 3", "class 5"))
        has_patent_intent = any(k in claim_lower for k in ("patent", "invention", "inventive step"))
        if has_tm_claim and not has_patent_intent:
            if any(k in src_topic or k in src_title for k in ("patent", "biodiversity", "biological")):
                return False

        # 2. Patent claim citing Trademark source
        has_patent_claim = any(k in claim_lower for k in ("patent", "section 3(p)", "section 3(e)", "inventive step", "prior art", "non-patentable"))
        if has_patent_claim and not has_tm_claim:
            if any(k in src_topic or k in src_title for k in ("trademark", "trade mark")):
                return False

        # 3. Biodiversity claim citing Trademark or Food source
        has_bio_claim = any(k in claim_lower for k in ("biological diversity", "nba approval", "state biodiversity board", "sbb intimation", "bio-survey", "biological resource"))
        if has_bio_claim:
            if any(k in src_topic or k in src_title for k in ("trademark", "aahar")):
                return False

        # 4. Ayurveda Aahar / dietary food claim citing Patent or Drug source
        has_aahar_claim = any(k in claim_lower for k in ("ayurveda aahar", "dietary food", "fssai", "food safety", "food labelling"))
        if has_aahar_claim:
            if any(k in src_topic or k in src_title for k in ("patent", "classical_medicine", "drug")):
                return False

        # 5. ASU manufacturing licensing citing Trademark source
        has_licensing_claim = any(k in claim_lower for k in ("manufacturing license", "form 25d", "form 24d", "rule 158"))
        if has_licensing_claim and not has_tm_claim:
            if any(k in src_topic or k in src_title for k in ("trademark", "trade mark")):
                return False

        return True

    @classmethod
    def is_source_supporting(cls, answer_text: str, source: SearchResultChunk) -> bool:
        """High-level check ensuring that the overall answer context does not suffer

        from global cross-domain contamination.
        """
        return cls.is_claim_supported_by_source(answer_text, source)

    @classmethod
    def extract_and_build_citations(
        cls, answer_text: str, retrieved_sources: List[SearchResultChunk]
    ) -> List[CitationDetail]:
        """Scans generated text for citation markers [1], [2], [Source 1], identifies the claim

        sentence associated with each citation, verifies claim-level statutory grounding,
        and constructs structured CitationDetail objects.
        """
        if not answer_text or not retrieved_sources:
            return []

        pattern = re.compile(r"\[(?:Source\s*)?([0-9]+(?:\s*,\s*[0-9]+)*)\]", re.IGNORECASE)
        valid_citations_map = {}

        for match in pattern.finditer(answer_text):
            claim_sentence = cls.get_enclosing_claim(answer_text, match.start(), match.end())
            matched_numbers = match.group(1)
            for part in matched_numbers.split(","):
                part = part.strip()
                if part.isdigit():
                    idx = int(part)
                    chunk_idx = idx - 1
                    if 0 <= chunk_idx < len(retrieved_sources):
                        src = retrieved_sources[chunk_idx]
                        if cls.is_claim_supported_by_source(claim_sentence, src):
                            valid_citations_map[idx] = src

        citations: List[CitationDetail] = []
        for idx in sorted(valid_citations_map.keys()):
            src = valid_citations_map[idx]

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
