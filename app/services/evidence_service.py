"""Evidence validation service verifying citation veracity, relevance, and conflict detection."""

from typing import List, Optional, Tuple
from app.schemas.chat import CitationDetail, ConfidenceDetail
from app.schemas.source import SearchResultChunk


class EvidenceService:
    """Evaluates evidence strength, verifies citations, and identifies conflicting authorities."""

    @staticmethod
    def validate_and_score_evidence(
        retrieved_sources: List[SearchResultChunk],
        citations: List[CitationDetail],
        selected_jurisdiction: str,
    ) -> Tuple[ConfidenceDetail, bool, Optional[str]]:
        """Performs multi-criteria evidence audit:

        1. Total chunks retrieved.
        2. Relevance score distribution.
        3. Jurisdiction alignment.
        4. Citation correspondence.
        5. Source conflict detection.
        """
        # 1. Check for insufficient evidence
        if not retrieved_sources:
            return (
                ConfidenceDetail(
                    level="INSUFFICIENT",
                    score=0.0,
                    reason="No authoritative documents or regulatory sections were retrieved matching the query."
                ),
                False,
                None,
            )

        # 2. Jurisdiction consistency check
        mismatched_jurisdictions = [
            s for s in retrieved_sources
            if s.jurisdiction.lower() != selected_jurisdiction.lower() and selected_jurisdiction.lower() != "all"
        ]

        # 3. Average relevance of top sources
        top_scores = [s.relevance_score for s in retrieved_sources[:3]]
        avg_relevance = sum(top_scores) / len(top_scores) if top_scores else 0.0

        # 4. Check citations match retrieved documents
        valid_citations = [
            c for c in citations if any(s.document_id == c.document_id for s in retrieved_sources)
        ]

        # 5. Potential conflict detection
        # e.g., If one source says patentable and another cites statutory bar like Section 3(p)
        conflict_detected = False
        conflict_warning = None

        has_patent_source = any("patent" in s.topic.lower() or "section 3" in (s.section_number or "").lower() for s in retrieved_sources)
        has_classical_source = any("classical" in s.topic.lower() or "first schedule" in s.chunk_text.lower() for s in retrieved_sources)

        # If evaluating a classical formulation for a patent, highlight the legal friction
        if has_patent_source and has_classical_source:
            conflict_detected = True
            conflict_warning = (
                "Potential legal nuance detected: Classical Ayurvedic formulations are traditionally protected "
                "under Indian Patents Act Section 3(p) as non-patentable traditional knowledge, whereas modern "
                "novel extraction processes or non-obvious synergistic combinations require distinct legal hurdles."
            )

        # 6. Assign confidence level
        if avg_relevance >= 0.70 and len(valid_citations) >= 1 and not mismatched_jurisdictions:
            level = "HIGH"
            score = round(min(0.95, avg_relevance + 0.1), 2)
            reason = (
                f"Strongly grounded in {len(retrieved_sources)} authoritative source chunk(s) "
                f"from {selected_jurisdiction} with high semantic and statutory alignment."
            )
        elif avg_relevance >= 0.40 and len(valid_citations) >= 1:
            level = "MEDIUM"
            score = round(avg_relevance, 2)
            reason = (
                f"Moderately grounded in {len(retrieved_sources)} source chunk(s). "
                "Contains relevant statutory guidance, though specific secondary provisions may require further review."
            )
        else:
            level = "LOW"
            score = round(max(0.25, avg_relevance), 2)
            reason = (
                "Retrieved sources provide peripheral context but limited direct statutory or case precedents."
            )

        return ConfidenceDetail(level=level, score=score, reason=reason), conflict_detected, conflict_warning
