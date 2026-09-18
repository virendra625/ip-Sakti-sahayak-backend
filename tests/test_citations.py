"""Tests for citation formatting, evidence validation, and anti-hallucination safeguards."""

from fastapi import status


def test_citation_structure_and_grounding(client):
    """Verifies that grounded response contains proper citation format."""
    payload = {
        "message": "What does Section 3(p) of the Patents Act say about traditional knowledge?",
        "jurisdiction": "India",
        "language": "en",
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "Patents Act" in data["answer"]
    assert len(data["citations"]) >= 1

    first_cit = data["citations"][0]
    assert first_cit["document_id"] > 0
    assert first_cit["authority"] != ""
    assert "[1]" in first_cit["citation_text"]
    assert "Authority:" in first_cit["citation_text"]
    assert "Version:" in first_cit["citation_text"]


def test_no_evidence_safeguard_prevents_hallucination(client):
    """Verifies that when query has no matching documents (e.g. unknown Martian law),

    system does NOT hallucinate fake citations and returns insufficient evidence warning.
    """
    payload = {
        "message": "What is the patent registration fee on planet Mars under Martian Treaty 4099?",
        "jurisdiction": "USA",  # No USA or Martian docs in DB
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    # Safeguard check:
    assert (
        "I could not find sufficient authoritative evidence" in data["answer"]
        or "sufficient authoritative evidence" in data["confidence"]["reason"]
    )
    assert data["confidence"]["level"] == "INSUFFICIENT"
    assert len(data["citations"]) == 0


def test_no_fallback_to_source_1_when_not_cited_in_text():
    """Verifies that if the answer text does NOT cite any source, CitationService
    does NOT attach Source 1 as a fallback.
    """
    from app.services.citation_service import CitationService
    from app.schemas.source import SearchResultChunk

    dummy_chunks = [
        SearchResultChunk(
            document_id=1,
            document_title="The Patents Act, 1970",
            authority="IPO",
            jurisdiction="India",
            topic="Patent",
            section_number="Section 3(p)",
            version="Current",
            chunk_text="Inventions relating to traditional knowledge are not patentable.",
            relevance_score=0.9,
        ),
        SearchResultChunk(
            document_id=2,
            document_title="Biological Diversity Act, 2002",
            authority="NBA",
            jurisdiction="India",
            topic="Biodiversity",
            section_number="Section 3",
            version="Current",
            chunk_text="Approval needed for biological resources.",
            relevance_score=0.8,
        ),
    ]

    uncited_answer = "This is a direct response that does not mention or cite any sources."
    citations = CitationService.extract_and_build_citations(uncited_answer, dummy_chunks)
    assert len(citations) == 0, "Fallback to {1} was removed; citations must be empty when none are cited."


def test_source_bracket_formatting_variants():
    """Verifies that CitationService parses both [1] and [Source 1] accurately."""
    from app.services.citation_service import CitationService
    from app.schemas.source import SearchResultChunk

    dummy_chunks = [
        SearchResultChunk(
            document_id=10,
            document_title="The Patents Act, 1970",
            authority="IPO",
            jurisdiction="India",
            topic="Patent",
            section_number="Section 3(p)",
            version="Current",
            chunk_text="Traditional knowledge exclusions.",
            relevance_score=0.95,
        ),
        SearchResultChunk(
            document_id=20,
            document_title="Drugs and Cosmetics Act, 1940",
            authority="Ministry of Ayush",
            jurisdiction="India",
            topic="Drug_Ayush",
            section_number="Rule 158B",
            version="Current",
            chunk_text="Proof of effectiveness requirements.",
            relevance_score=0.85,
        ),
    ]

    # Test [Source 1] format
    text_source_style = "Section 3(p) bars patenting traditional knowledge. [Source 1]"
    citations_1 = CitationService.extract_and_build_citations(text_source_style, dummy_chunks)
    assert len(citations_1) == 1
    assert citations_1[0].document_id == 10

    # Test [2] format
    text_numeric_style = "Rule 158B governs proof of effectiveness. [2]"
    citations_2 = CitationService.extract_and_build_citations(text_numeric_style, dummy_chunks)
    assert len(citations_2) == 1
    assert citations_2[0].document_id == 20

    # Test multi-citation [Source 1, Source 2] or [1, 2]
    text_multi = "Both provisions apply here. [1, 2]"
    citations_multi = CitationService.extract_and_build_citations(text_multi, dummy_chunks)
    assert len(citations_multi) == 2


def test_only_supporting_sources_returned_in_chat(client):
    """Verifies that ChatResponse only includes sources that actually support the answer."""
    payload = {
        "message": "What does Section 3(p) say about patenting traditional knowledge?",
        "jurisdiction": "India",
        "language": "en",
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # The sources array must only contain cited/supporting chunks
    assert len(data["sources"]) == len(data["citations"])
    cited_ids = {c["document_id"] for c in data["citations"]}
    for src in data["sources"]:
        assert src["document_id"] in cited_ids

