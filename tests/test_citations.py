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
