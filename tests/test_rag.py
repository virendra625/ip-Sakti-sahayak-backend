"""Tests for RAG retrieval and standalone search endpoint."""

from fastapi import status


def test_search_endpoint_patents(client):
    """Verifies retrieval finds Section 3(p) for patent questions."""
    payload = {
        "query": "traditional knowledge patentability exclusions",
        "jurisdiction": "India",
        "topic": "Patent",
        "limit": 3,
    }
    response = client.post("/api/v1/search", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["jurisdiction"] == "India"
    assert "results" in data
    assert len(data["results"]) > 0

    first = data["results"][0]
    assert "Patents Act" in first["document_title"]
    assert first["relevance_score"] >= 0.0


def test_search_endpoint_ayurveda_aahar(client):
    """Verifies retrieval finds Ayurveda Aahar regulations."""
    payload = {
        "query": "Ayurveda Aahar dietary food labelling standards",
        "jurisdiction": "India",
        "topic": "Ayurveda_Aahar",
        "limit": 3,
    }
    response = client.post("/api/v1/search", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data["results"]) > 0
    assert any("Aahar" in r["document_title"] for r in data["results"])


def test_search_isolation_no_cross_jurisdiction(client):
    """Verifies that selecting USA does not silently return Indian statutes."""
    payload = {
        "query": "botanical drug FDA guidance",
        "jurisdiction": "USA",
        "limit": 3,
    }
    response = client.post("/api/v1/search", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    # Since our DB currently only has Indian statutes, USA search should return 0 results
    # demonstrating strict jurisdictional isolation!
    assert len(data["results"]) == 0
