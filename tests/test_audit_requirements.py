"""Acceptance test suite for the IP-SAKTI Sahayak backend.

Covers all 12 core requirements and 4 functional domain questions:
1. Official patent URL is valid.
2. Official trademark URL is valid.
3. Official biodiversity URL is valid.
4. Official Ayurveda-Aahar URL is valid.
5. Official drugs/ASU URL is valid.
6. Unverified URLs are removed/rejected.
7. No 'DEMO DATA — NOT AUTHORITATIVE' remains in data/documents.
8. Mock LLM has no hardcoded topic-routing branches.
9. Citation source matches the relevant retrieved domain/topic.
10. Classification uses conditional legal language.
11. Multilingual questions are handled (English, Hindi, Hinglish).
12. Insufficient evidence does not produce fabricated citations.

Functional questions:
A. Trademark-related question
B. Patent-related question
C. Ayurveda-Aahar question
D. Biodiversity / biological-resource question
"""

import inspect
from pathlib import Path
import pytest
from fastapi import status

from app.core.config import settings
from app.rag.retriever import get_retriever
from app.schemas.classification import ProductClassificationRequest
from app.schemas.source import SearchResultChunk
from app.services.citation_service import CitationService
from app.services.classification_service import ClassificationService
from app.services.llm_service import MockLLMProvider
from app.services.url_service import URLService


# ==============================================================================
# Requirement 1 to 5: Official Statutory URLs
# ==============================================================================


def test_official_patent_url_valid():
    """1. Official patent URL is valid, official domain, and verified."""
    url = URLService.OFFICIAL_URL_PATENT
    assert url == "https://ipindia.gov.in/resource/patents-resources-act"
    assert URLService.is_url_verified(url)
    assert URLService.is_official_domain(url)


def test_official_trademark_url_valid():
    """2. Official trademark URL is valid, official domain, and verified."""
    url = URLService.OFFICIAL_URL_TRADEMARK
    assert url == "https://ipindia.gov.in/trade-marks-resources-act"
    assert URLService.is_url_verified(url)
    assert URLService.is_official_domain(url)


def test_official_biodiversity_url_valid():
    """3. Official biodiversity URL is valid on nbaindia.nic.in, and nbaindia.org is rejected."""
    url = URLService.OFFICIAL_URL_BIODIVERSITY
    assert url == "https://nbaindia.nic.in/acts-and-rules/acts"
    assert URLService.is_url_verified(url)
    assert URLService.is_official_domain(url)

    # Verify obsolete domain is rejected
    assert not URLService.is_url_verified("https://nbaindia.org/act")
    assert not URLService.is_official_domain("https://nbaindia.org")


def test_official_ayurveda_aahar_url_valid():
    """4. Official Ayurveda-Aahar URL is valid on fssai.gov.in."""
    url = URLService.OFFICIAL_URL_AYURVEDA_AAHAR
    assert "fssai.gov.in" in url
    assert "Ayurveda_Aahar" in url
    assert URLService.is_url_verified(url)
    assert URLService.is_official_domain(url)


def test_official_drugs_asu_url_valid():
    """5. Official drugs/ASU URL is valid on cdsco.gov.in."""
    url = URLService.OFFICIAL_URL_DRUGS_ASU
    assert "cdsco.gov.in" in url
    assert URLService.is_url_verified(url)
    assert URLService.is_official_domain(url)


# ==============================================================================
# Requirement 6: Unverified URLs Removed/Rejected
# ==============================================================================


def test_unverified_urls_removed_or_rejected():
    """6. Unverified or fabricated URLs are stripped/sanitized from answer text

    and not blindly replaced with random verified URLs from the same domain.
    """
    sample_text = (
        "Check this unverified source https://fake-law-portal.com/patents and this "
        "arbitrary subpage https://ipindia.gov.in/random-unknown-fake-page.pdf for details."
    )
    sanitized = URLService.validate_and_sanitize_answer_urls(sample_text)

    # Unverified domains and unverified pages on official domains must be stripped
    assert "https://fake-law-portal.com/patents" not in sanitized
    assert "https://ipindia.gov.in/random-unknown-fake-page.pdf" not in sanitized
    assert "[official government record]" in sanitized

    # Verified URLs must be preserved
    verified_text = f"Official statute: {URLService.OFFICIAL_URL_PATENT}"
    assert URLService.validate_and_sanitize_answer_urls(verified_text) == verified_text


# ==============================================================================
# Requirement 7: Source Metadata Quality
# ==============================================================================


def test_no_demo_data_header_remains():
    """7. Verifies no 'DEMO DATA — NOT AUTHORITATIVE' remains in any data/documents file,

    and that appropriate curated excerpt notices exist.
    """
    docs_dir = Path(__file__).resolve().parent.parent / "data" / "documents"
    files = list(docs_dir.glob("*.txt"))
    assert len(files) >= 5, "Expected at least 5 document files"

    for f in files:
        content = f.read_text(encoding="utf-8")
        assert "DEMO DATA — NOT AUTHORITATIVE" not in content, f"Found DEMO DATA in {f.name}"
        assert "Curated source excerpt" in content, f"Missing curated excerpt notice in {f.name}"
        assert "Source URL: https://" in content, f"Missing official source URL in {f.name}"


# ==============================================================================
# Requirement 8: Mock LLM Has No Hardcoded Topic-Routing Branches
# ==============================================================================


def test_mock_llm_no_hardcoded_topic_routing_branches():
    """8. Verifies MockLLMProvider contains no hardcoded topic routing flags

    (e.g. is_tm_query, is_patent_query, is_licensing_query, is_aahar_query, _find_source_index).
    """
    source_code = inspect.getsource(MockLLMProvider)
    forbidden_terms = [
        "is_tm_query",
        "is_patent_query",
        "is_licensing_query",
        "is_aahar_query",
        "_find_source_index",
    ]
    for term in forbidden_terms:
        assert term not in source_code, f"Found forbidden hardcoded branch flag '{term}' in MockLLMProvider"


# ==============================================================================
# Requirement 9: Claim-Level Citation Verification
# ==============================================================================


def test_citation_source_matches_relevant_domain():
    """9. Verifies claim-level citation validation rejects cross-domain attributions."""
    patent_chunk = SearchResultChunk(
        document_id=1,
        document_title="The Patents Act, 1970",
        authority="IPO",
        jurisdiction="India",
        topic="Patent",
        section_number="Section 3(p)",
        chunk_text="Inventions relating to traditional knowledge are not patentable.",
        relevance_score=0.9,
        version="current",
    )
    trademark_chunk = SearchResultChunk(
        document_id=2,
        document_title="Trade Marks Act, 1999",
        authority="CGPDTM",
        jurisdiction="India",
        topic="Trademark",
        section_number="Section 2(1)(zb)",
        chunk_text="A trade mark distinguishes goods or services.",
        relevance_score=0.9,
        version="current",
    )
    food_chunk = SearchResultChunk(
        document_id=3,
        document_title="Ayurveda Aahar Regulations, 2022",
        authority="FSSAI",
        jurisdiction="India",
        topic="Ayurveda_Aahar",
        section_number="Regulation 3",
        chunk_text="Ayurveda Aahar food standards.",
        relevance_score=0.85,
        version="current",
    )

    # Cross-domain claim: Trademark statement citing Patent chunk
    tm_claim = "You can register your brand name as a trademark. [Source 1]"
    citations = CitationService.extract_and_build_citations(tm_claim, [patent_chunk])
    assert len(citations) == 0, "Trademark claim must NOT be supported by a Patent source."

    # Cross-domain claim: Patent claim citing Trademark chunk
    patent_claim = "Classical formulations are non-patentable under Section 3(p). [Source 1]"
    citations2 = CitationService.extract_and_build_citations(patent_claim, [trademark_chunk])
    assert len(citations2) == 0, "Patent claim must NOT be supported by a Trademark source."

    # Matching claim: Trademark claim citing Trademark chunk
    valid_tm = CitationService.extract_and_build_citations(tm_claim, [trademark_chunk])
    assert len(valid_tm) == 1
    assert valid_tm[0].document_title == "Trade Marks Act, 1999"


# ==============================================================================
# Requirement 10: Conditional Legal Language in Classification
# ==============================================================================


def test_classification_uses_conditional_legal_language():
    """10. Verifies classification outputs avoid absolute legal assertions and use conditional phrasing."""
    req = ProductClassificationRequest(
        product_name="Maha Triphala Taila",
        product_description="Classical Ayurvedic oil prepared strictly according to Sharangadhara Samhita scriptures.",
        intended_use="Therapeutic application for eye disorders.",
        is_classical_text_source=True,
        has_formulation_been_modified=False,
    )
    resp = ClassificationService.classify_product(req)
    assert resp.likely_category == "Classical_ASU_Medicine"

    # Must NOT have absolute declarations
    for imp in resp.ipr_implications:
        assert "Strictly NON-PATENTABLE" not in imp
        assert "Always prohibited" not in imp

    # Must contain conditional phrasing
    combined_implications = " ".join(resp.ipr_implications)
    assert any(w in combined_implications.lower() for w in ["generally", "unless", "may", "requires"])
    assert "informational" in resp.disclaimer.lower()


# ==============================================================================
# Requirement 11: Multilingual Language Support
# ==============================================================================


def test_multilingual_questions_handled(client):
    """11. Verifies English, Hindi, and Hinglish queries are handled and return appropriate language answers."""
    # English
    r_en = client.post("/api/v1/chat", json={"message": "What is a trademark?", "language": "en"})
    assert r_en.status_code == status.HTTP_200_OK
    assert r_en.json()["language"] == "en"

    # Hindi
    r_hi = client.post("/api/v1/chat", json={"message": "ट्रेडमार्क क्या होता है?", "language": "hi"})
    assert r_hi.status_code == status.HTTP_200_OK
    assert r_hi.json()["language"] == "hi"

    # Hinglish
    r_hng = client.post("/api/v1/chat", json={"message": "Trademark kya hota hai?", "language": "hinglish"})
    assert r_hng.status_code == status.HTTP_200_OK
    assert r_hng.json()["language"] in ["hinglish", "hi"]


# ==============================================================================
# Requirement 12: Insufficient Evidence Safeguard
# ==============================================================================


def test_insufficient_evidence_does_not_produce_fabricated_citations(client):
    """12. Out-of-scope query returns insufficient evidence warning with zero fabricated citations."""
    resp = client.post(
        "/api/v1/chat",
        json={"message": "What is the orbital trajectory of Voyager 1 in 2026?", "jurisdiction": "India"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data["citations"]) == 0
    assert len(data["sources"]) == 0
    assert "sufficient" in data["answer"].lower() or "reliable source" in data["answer"].lower()


# ==============================================================================
# Four Functional Domain Questions
# ==============================================================================


def test_functional_question_a_trademark(client):
    """Functional Question A: Trademark brand protection query."""
    resp = client.post(
        "/api/v1/chat",
        json={"message": "I want to launch an Ayurvedic hair oil. How can I protect my brand?", "language": "en"},
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    ans = data["answer"]

    # Properties check
    assert "brand" in ans.lower() or "trademark" in ans.lower()
    assert "Section 3(p)" not in ans
    assert "Patents Act" not in ans
    for cit in data["citations"]:
        assert "Trade Mark" in cit["document_title"]


def test_functional_question_b_patent(client):
    """Functional Question B: Classical Ayurvedic texts + new combination patent query."""
    resp = client.post(
        "/api/v1/chat",
        json={
            "message": "I am using classical Ayurvedic texts and creating a new combination. Can I patent it?",
            "language": "en",
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    ans = data["answer"]

    # Properties check
    assert "Section 3(p)" in ans or "Patents Act" in ans
    assert "Trade Mark" not in ans
    for cit in data["citations"]:
        assert "Patent" in cit["document_title"]


def test_functional_question_c_ayurveda_aahar(client):
    """Functional Question C: Ayurveda-Aahar dietary food regulatory query."""
    resp = client.post(
        "/api/v1/chat",
        json={
            "message": "What are the labelling and packaging standards for Ayurveda Aahar food products?",
            "language": "en",
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    ans = data["answer"]

    # Properties check
    assert "aahar" in ans.lower()
    for cit in data["citations"]:
        assert "Aahar" in cit["document_title"]


def test_functional_question_d_biodiversity(client):
    """Functional Question D: Biodiversity / Indian biological herbs query."""
    resp = client.post(
        "/api/v1/chat",
        json={
            "message": "Do I need National Biodiversity Authority approval for utilizing Indian biological herbs?",
            "language": "en",
        },
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    ans = data["answer"]

    # Properties check
    assert "biodiversity" in ans.lower() or "nba" in ans.lower() or "biological" in ans.lower()
    for cit in data["citations"]:
        assert "Biological Diversity" in cit["document_title"]
        assert "nbaindia.nic.in" in cit["source_url"]
