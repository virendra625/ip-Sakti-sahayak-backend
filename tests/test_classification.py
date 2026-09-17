"""Tests for Ayurvedic product regulatory classification endpoint."""

from fastapi import status


def test_classify_classical_asu_medicine(client):
    """Verifies that an unmodified Charaka Samhita formulation is classified as Classical ASU."""
    payload = {
        "product_name": "Classical Triphala Churna",
        "product_description": "Traditional Ayurvedic herbal powder made strictly following the formula in Charaka Samhita with Haritaki, Bibhitaki, and Amalaki in equal ratios.",
        "ingredients": ["Terminalia chebula", "Terminalia bellirica", "Phyllanthus emblica"],
        "formulation_information": "From Charaka Samhita classical text.",
        "is_classical_text_source": True,
        "has_formulation_been_modified": False,
        "intended_use": "Digestive health and therapeutic rejuvenation",
        "biological_resources_used": "Wild-harvested Indian herbs",
        "jurisdiction": "India",
    }
    response = client.post("/api/v1/classification", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["likely_category"] == "Classical_ASU_Medicine"
    assert data["confidence"] >= 0.85
    assert "Section 3(p)" in " ".join(data["ipr_implications"])
    assert "Likely classification" in data["disclaimer"]


def test_classify_proprietary_medicine(client):
    """Verifies modified formulation is classified as Patent or Proprietary Medicine."""
    payload = {
        "product_name": "Fortified Curcumin Drops",
        "product_description": "An aqueous extract of Curcuma longa fortified with piperine to enhance bioavailability, presented in liquid drops.",
        "ingredients": ["Curcuma longa", "Piperine"],
        "is_classical_text_source": False,
        "has_formulation_been_modified": True,
        "intended_use": "Anti-inflammatory support",
        "jurisdiction": "India",
    }
    response = client.post("/api/v1/classification", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["likely_category"] == "Patent_or_Proprietary_Medicine"
    assert data["confidence"] >= 0.80
    assert "Proprietary_Medicine" in data["relevant_topics"]


def test_classify_ayurveda_aahar(client):
    """Verifies dietary/food product is classified as Ayurveda Aahar."""
    payload = {
        "product_name": "Herbal Morning Breakfast Granules",
        "product_description": "Dietary health food made from roasted barley, cardamom, and jaggery as per Ayurvedic recipes for daily breakfast nutrition.",
        "intended_use": "Dietary food and nutrition consumption, not for disease treatment",
        "jurisdiction": "India",
    }
    response = client.post("/api/v1/classification", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["likely_category"] == "Ayurveda_Aahar"
    assert "Ayurveda_Aahar" in data["relevant_topics"]


def test_classify_insufficient_information(client):
    """Verifies that vague or empty inputs return Insufficient_Information with clarifying questions."""
    payload = {
        "product_description": "Some herbal powder",
    }
    response = client.post("/api/v1/classification", json=payload)
    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["likely_category"] == "Insufficient_Information"
    assert len(data["missing_information"]) > 0


def test_classify_empty_description_rejected(client):
    """Verifies validation error on blank description."""
    payload = {
        "product_description": "",
    }
    response = client.post("/api/v1/classification", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
