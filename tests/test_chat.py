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


def test_prompt_templates_hindi_no_hardcoded_english():
    """Verifies that Hindi prompt construction does not inject hardcoded English response headers."""
    from app.rag.prompt_templates import build_user_prompt, get_system_prompt

    sys_prompt = get_system_prompt(language="hi", jurisdiction="India")
    assert "Hindi" in sys_prompt
    assert "You are IP-SAKTI Sahayak" in sys_prompt
    assert "ANSWER THE USER'S ACTUAL QUESTION" in sys_prompt

    user_prompt = build_user_prompt(
        user_query="क्या मुझे अपने उत्पाद के लिए ट्रेडमार्क लेना चाहिए?",
        sources_block="[Source 1] Trade Marks Act, 1999",
        product_context_block="None",
        language="hi",
    )
    # Ensure no English instructions like "ANSWER:" or "USER QUESTION:" that could bias the LLM into English
    assert "USER QUESTION:" not in user_prompt
    assert "ANSWER (" not in user_prompt
    assert "उपयोगकर्ता का प्रश्न:" in user_prompt
    assert "पुनर्प्राप्त स्रोत" in user_prompt


def test_different_questions_receive_different_answers(client):
    """Verifies that different user questions receive tailored, non-generic answers."""
    # 1. Greeting
    r1 = client.post("/api/v1/chat", json={"message": "Hello, who are you?", "jurisdiction": "India", "language": "en"})
    assert r1.status_code == status.HTTP_200_OK
    a1 = r1.json()["answer"]
    assert "Section 3(p)" not in a1
    assert "How can I assist you" in a1 or "IP-SAKTI Sahayak" in a1

    # 2. Missing Information / Hair oil consultation
    r2 = client.post("/api/v1/chat", json={"message": "I am making an Ayurvedic hair oil. What information is needed?", "jurisdiction": "India", "language": "en"})
    assert r2.status_code == status.HTTP_200_OK
    a2 = r2.json()["answer"]
    assert "intended use" in a2.lower()
    assert "ingredients" in a2.lower()
    assert "Section 3(p)" not in a2

    # 3. Trademark Question
    r3 = client.post("/api/v1/chat", json={"message": "Can I register a trademark for my herbal formulation name?", "jurisdiction": "India", "language": "en"})
    assert r3.status_code == status.HTTP_200_OK
    a3 = r3.json()["answer"]
    assert "Trade Marks Act" in a3 or "Class 5" in a3 or "trademark" in a3.lower()

    # 4. Patent / Section 3(p) Question
    r4 = client.post("/api/v1/chat", json={"message": "Can a classical Ayurvedic medicine be patented in India?", "jurisdiction": "India", "language": "en"})
    assert r4.status_code == status.HTTP_200_OK
    a4 = r4.json()["answer"]
    assert "Section 3(p)" in a4 or "Patents Act" in a4

    # All answers must be distinct
    answers = {a1, a2, a3, a4}
    assert len(answers) == 4, "Every distinct question must receive a distinct tailored answer."


def test_hinglish_language_handling(client):
    """Verifies that conversational Hinglish questions are handled properly."""
    payload = {
        "message": "kya classical aushadhi ka patent ho sakta hai?",
        "jurisdiction": "India",
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["language"] in ["hinglish", "hi"]
    assert len(data["answer"]) > 10


def test_conversation_history_persistence_and_context(client):
    """Verifies that multi-turn conversations persist history and pass context to prompt."""
    conv_id = "test-conv-context-101"

    # Turn 1
    r1 = client.post("/api/v1/chat", json={
        "message": "I have created an herbal hair oil. What information do you need?",
        "conversation_id": conv_id,
        "jurisdiction": "India",
        "language": "en",
    })
    assert r1.status_code == status.HTTP_200_OK
    assert r1.json()["conversation_id"] == conv_id

    # Turn 2 (Follow-up providing details)
    r2 = client.post("/api/v1/chat", json={
        "message": "It uses classical bhringraj and amla from Charaka Samhita. Can I patent it?",
        "conversation_id": conv_id,
        "jurisdiction": "India",
        "language": "en",
    })
    assert r2.status_code == status.HTTP_200_OK
    assert r2.json()["conversation_id"] == conv_id
    assert "Section 3(p)" in r2.json()["answer"] or "Patents Act" in r2.json()["answer"]


def test_insufficient_evidence_admission(client):
    """Verifies that out-of-scope queries with no matching sources admit missing evidence."""
    payload = {
        "message": "What is the orbital trajectory of Voyager 1 in 2026?",
        "jurisdiction": "India",
        "language": "en",
    }
    response = client.post("/api/v1/chat", json=payload)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "no sufficiently relevant source" in data["answer"].lower() or "reliable source information" in data["answer"].lower()
    assert len(data["citations"]) == 0
    assert len(data["sources"]) == 0



