"""Tests for jurisdiction handling, boundaries, and taxonomy."""

from fastapi import status


def test_list_jurisdictions(client):
    """Verifies GET /api/v1/jurisdictions returns active jurisdictions."""
    response = client.get("/api/v1/jurisdictions")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert len(data) >= 4
    names = [j["name"] for j in data]
    assert "India" in names
    assert "International" in names
    assert "USA" in names


def test_list_topics(client):
    """Verifies GET /api/v1/topics returns complete taxonomy."""
    response = client.get("/api/v1/topics")
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "domains" in data
    assert "ipr_topics" in data
    assert "regulatory_topics" in data
    assert "Patent" in data["ipr_topics"]
    assert "Classical_Medicine" in data["regulatory_topics"]


def test_missing_jurisdiction_on_patent_question(client):
    """Verifies that an open patentability question with no jurisdiction requests clarification."""
    payload = {
        "message": "Can I patent this classical formulation?",
        "jurisdiction": None,
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert "Which jurisdiction should I analyse?" in data["answer"]
    assert data["confidence"]["level"] == "INSUFFICIENT"
