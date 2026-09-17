"""Tests for conversational chat turns, Hindi queries, and feedback."""

from fastapi import status


def test_chat_english_grounded(client):
    """Verifies English chat query returns grounded answer with citations and disclaimer."""
    payload = {
        "message": "Can a classical Ayurvedic medicine be patented in India?",
        "jurisdiction": "India",
        "language": "en",
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["language"] == "en"
    assert data["jurisdiction"] == "India"
    assert "answer" in data
    assert len(data["answer"]) > 20
    assert len(data["citations"]) > 0
    assert "disclaimer" in data
    assert "informational" in data["disclaimer"].lower()


def test_chat_hindi_query(client):
    """Verifies Hindi query returns Hindi explanation while citing authentic English sources."""
    payload = {
        "message": "क्या मैं शास्त्रीय आयुर्वेदिक दवा का भारत में पेटेंट करा सकता हूँ?",
        "jurisdiction": "India",
        "language": "hi",
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["language"] == "hi"
    assert "आधिकारिक स्रोतों" in data["answer"] or "पेटेंट" in data["answer"]
    assert len(data["citations"]) > 0
    # Original source citation remains authentic and non-translated:
    assert data["citations"][0]["document_title"] != ""
    assert "निर्णय-समर्थन" in data["disclaimer"]


def test_chat_with_product_context(client):
    """Verifies chat endpoint integrates product classification when product_context is provided."""
    payload = {
        "message": "What regulatory approvals do I need for this formulation?",
        "jurisdiction": "India",
        "language": "en",
        "product_context": {
            "product_name": "Digestive Herbal Tea",
            "product_description": "Dietary health beverage prepared with ginger and peppermint for daily digestion, not intended to cure disease.",
            "intended_use": "Dietary nutrition",
            "jurisdiction": "India",
        },
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["product_classification"] is not None
    assert data["product_classification"]["likely_category"] == "Ayurveda_Aahar"


def test_submit_feedback(client):
    """Verifies user evaluation feedback endpoint."""
    feedback_payload = {
        "rating": "helpful",
        "comment": "Accurately cited Section 3(p) of the Indian Patents Act.",
    }
    response = client.post("/api/v1/feedback", json=feedback_payload)
    assert response.status_code == status.HTTP_201_CREATED

    data = response.json()
    assert data["rating"] == "helpful"
    assert data["feedback_id"] > 0
