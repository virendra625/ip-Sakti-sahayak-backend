"""Tests for document registration, retrieval, and source listing."""

from fastapi import status


def test_ingest_and_list_documents(client):
    """Verifies that an authoritative document can be ingested via API and listed."""
    ingest_payload = {
        "title": "Guidelines on Patent Applications in the Field of Pharmaceuticals",
        "authority": "Office of the Controller General of Patents, Designs & Trade Marks",
        "jurisdiction": "India",
        "country": "India",
        "document_type": "government_guideline",
        "topic": "Patent",
        "version": "2014_guideline",
        "text_content": (
            "Section 3(p): Inventions relating to traditional knowledge. "
            "Guidelines state that claims relating to extracts of plants already disclosed "
            "in Ayurvedic texts must demonstrate surprising or non-additive therapeutic synergy."
        ),
        "source_url": "https://ipindia.gov.in",
        "language": "en",
        "description": "Guidelines for examination of pharmaceutical patent applications.",
    }
    response = client.post("/api/v1/documents/ingest", json=ingest_payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    doc_id = data["document_id"]
    assert doc_id > 0
    assert data["total_chunks"] >= 1

    # Fetch document by ID
    get_resp = client.get(f"/api/v1/documents/{doc_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["title"] == ingest_payload["title"]

    # Verify document is in /api/v1/sources
    sources_resp = client.get("/api/v1/sources?topic=Patent")
    assert sources_resp.status_code == status.HTTP_200_OK
    titles = [s["title"] for s in sources_resp.json()]
    assert ingest_payload["title"] in titles
