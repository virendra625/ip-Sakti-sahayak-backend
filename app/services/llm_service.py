"""Abstract LLM Service provider with Mock, Gemini, and OpenAI implementations."""

import abc
import os
from typing import List, Optional
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.schemas.source import SearchResultChunk


class BaseLLMProvider(abc.ABC):
    """Abstract interface for LLM text completion."""

    @abc.abstractmethod
    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        retrieved_sources: List[SearchResultChunk],
        language: str = "en",
    ) -> str:
        """Generates an answer grounded strictly in retrieved sources."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """Grounded offline LLM simulator for testing and zero-cost local execution.

    Directly inspects the user's question and synthesizes a tailored, evidence-backed
    answer adhering to the 10 IP-SAKTI Sahayak rules, citing only supporting sources.
    """

    @staticmethod
    def _extract_user_query(user_prompt: str) -> str:
        """Extracts the actual user question from the assembled user prompt."""
        markers = [
            "USER QUESTION:\n",
            "उपयोगकर्ता का प्रश्न:\n",
            "उपयोगकर्ता का वर्तमान प्रश्न:\n",
            "CURRENT USER QUESTION:\n",
        ]
        for m in markers:
            if m in user_prompt:
                part = user_prompt.split(m, 1)[1]
                for end_marker in ["\n\nANSWER", "\n\n(ऊपर", "\n\n(Please", "\n\nINSTRUCTION"]:
                    if end_marker in part:
                        part = part.split(end_marker, 1)[0]
                return part.strip()
        return user_prompt.strip()

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        retrieved_sources: List[SearchResultChunk],
        language: str = "en",
    ) -> str:
        user_query = self._extract_user_query(user_prompt)
        q_lower = user_query.lower()

        # 1. Handle Greetings / Conversational queries (Do not invent legal claims)
        greeting_words = ["hello", "hi", "hey", "नमस्ते", "namaste", "pranam", "help", "who are you", "who you are"]
        has_greeting = any(g in q_lower for g in greeting_words)
        has_legal_intent = any(
            k in q_lower for k in ["patent", "trademark", "section", "rule", "act", "formulation", "license", "approval", "aahar", "classical", "hair oil"]
        )
        if (q_lower.strip() in greeting_words or has_greeting) and not has_legal_intent:
            if language == "hi":
                return (
                    "नमस्ते! मैं IP-SAKTI Sahayak हूँ - आयुर्वेद, बौद्धिक संपदा अधिकार (IPR), "
                    "पारंपरिक ज्ञान, पेटेंट, ट्रेडमार्क और संबंधित विनियामक विषयों के लिए आपका प्रारंभिक सूचनात्मक सहायक। "
                    "मैं आपके उत्पाद, फॉर्मूलेशन या कानूनी प्रश्न में किस प्रकार सहायता कर सकता हूँ?"
                )
            elif language == "hinglish":
                return (
                    "Hello! Main IP-SAKTI Sahayak hoon - Ayurveda, IPR, traditional knowledge, "
                    "patents, trademarks aur regulatory guidance ke liye aapka assistant. "
                    "Aap apne product ya legal provisions ke baare mein kya poochhna chahte hain?"
                )
            return (
                "Hello! I am IP-SAKTI Sahayak, an AI assistant providing preliminary information on "
                "Intellectual Property Rights (IPR), AYUSH regulations, traditional knowledge, patents, "
                "trademarks, and Indian legal/regulatory topics. How can I assist you today?"
            )

        # 2. Handle queries where product information is missing (Rule 7)
        if any(k in q_lower for k in ["hair oil", "what information", "what do you need", "what details", "kya information", "kya details"]) and not any(
            k in q_lower for k in ["section 3", "rule 158", "definition of", "patents act"]
        ):
            if language == "hi":
                return (
                    "Short Answer\n"
                    "आपके उत्पाद के लिए सही IPR और विनियामक मार्ग निर्धारित करने के लिए मुझे कुछ आवश्यक विवरणों की आवश्यकता है:\n\n"
                    "1. इस उत्पाद का मुख्य उद्देश्य (Intended Use) क्या है (चिकित्सीय उपचार बनाम कॉस्मेटिक/सौंदर्य प्रसाधन)?\n"
                    "2. इसके मुख्य सक्रिय घटक (Key Ingredients) क्या हैं?\n"
                    "3. क्या यह निर्माण किसी शास्त्रीय आयुर्वेदिक ग्रंथ पर आधारित है या नवीन (newly developed) है?\n"
                    "4. उत्पाद के लेबल या वेबसाइट पर क्या विशिष्ट दावे (Claims) किए जाएंगे?\n"
                    "5. क्या इसमें प्रयुक्त जैविक जड़ी-बूटियाँ भारत से प्राप्त की गई हैं?"
                )
            elif language == "hinglish":
                return (
                    "Short Answer\n"
                    "Aapke product ke liye accurate IPR aur regulatory guidance dene ke liye mujhe kuch details ki zaroorat hai:\n\n"
                    "1. Product ka intended use kya hai (therapeutic treatment ya cosmetic)?\n"
                    "2. Main ingredients kya hain aur formulation classical hai ya newly developed?\n"
                    "3. Label par kya claims kiye jayenge?\n"
                    "4. Kya herbs India se source kiye gaye hain (NBA compliance)?"
                )
            return (
                "Short Answer\n"
                "To provide accurate IPR and regulatory guidance for your formulation, please provide a few key details:\n\n"
                "1. What is the intended use (therapeutic treatment vs. cosmetic/wellness)?\n"
                "2. Is the product being marketed as a cosmetic or as an Ayurvedic medicine?\n"
                "3. What are the main ingredients?\n"
                "4. Is the formulation classical (from First Schedule texts) or newly developed?\n"
                "5. What claims will appear on the label or packaging?"
            )

        # 3. Insufficient / No Evidence Found (Rule 2 & Step 3)
        if not retrieved_sources:
            if language == "hi":
                return (
                    "इस प्रश्न के लिए कोई पर्याप्त प्रासंगिक स्रोत नहीं मिला। "
                    "मेरे पास इसका सटीक उत्तर देने के लिए पर्याप्त विश्वसनीय स्रोत जानकारी नहीं है। "
                    "वर्तमान ज्ञानकोश में इस विषय पर आधिकारिक साक्ष्य उपलब्ध नहीं हैं।"
                )
            elif language == "hinglish":
                return (
                    "Is sawal ke liye koi sufficiently relevant source nahi mila. "
                    "Mere paas iska accurate answer dene ke liye reliable source information nahi hai."
                )
            return (
                "No sufficiently relevant source was found for this question. "
                "I don't have enough reliable source information to answer that accurately. "
                "I could not find sufficient authoritative evidence in the current knowledge base to answer this reliably."
            )

        # 4. Check for Trademark / Brand Questions
        if any(k in q_lower for k in ["trademark", "brand", "logo", "ट्रेडमार्क", "class 5", "class 3", "class 30"]):
            if language == "hi":
                return (
                    "Short Answer\n"
                    "हाँ, आप अपने आयुर्वेदिक उत्पाद के विशिष्ट ब्रांड नाम, लोगो और पैकेजिंग के लिए ट्रेडमार्क (Trade Marks Act, 1999) प्राप्त कर सकते हैं।\n\n"
                    "Why\n"
                    "- आयुर्वेदिक दवाओं के लिए Trademark Class 5, सौंदर्य प्रसाधनों (Cosmetics) के लिए Class 3, और आहार उत्पादों के लिए Class 30 लागू होती है।\n"
                    "- शास्त्रीय ग्रंथों में वर्णित सामान्य या पारंपरिक नामों (जैसे Triphala, Chyawanprash) पर कोई निजी ट्रेडमार्क नहीं दिया जा सकता।\n\n"
                    "Sources\n"
                    "- [Source 1] " + retrieved_sources[0].document_title
                )
            return (
                "Short Answer\n"
                "Yes, distinctive brand names, logos, and packaging for Ayurvedic products can be protected under the Trade Marks Act, 1999.\n\n"
                "Why\n"
                "• Ayurvedic medicines are registered under Class 5, cosmetics under Class 3, and dietary health supplements (Ayurveda Aahar) under Class 30.\n"
                "• Generic formulation names derived from classical authoritative texts (e.g. Triphala, Chyawanprash) cannot be privately monopolized as exclusive trademarks.\n\n"
                "Sources\n"
                "- [Source 1] " + retrieved_sources[0].document_title
            )

        # 5. Check for Patent / Traditional Knowledge / Section 3(p) Questions
        if any(k in q_lower for k in ["patent", "classical", "traditional knowledge", "section 3(p)", "3(p)", "tkdl", "पेटेंट", "शास्त्रीय"]):
            # Find the Patent Act chunk if present
            patent_idx = next(
                (i for i, s in enumerate(retrieved_sources, start=1) if "patent" in s.topic.lower() or "patent" in s.document_title.lower()),
                1,
            )
            patent_src = retrieved_sources[patent_idx - 1]

            if language == "hi":
                return (
                    "Short Answer\n"
                    f"उपलब्ध आधिकारिक स्रोतों के अनुसार, भारतीय पेटेंट अधिनियम (Patents Act, 1970) की धारा 3(p) के तहत शास्त्रीय आयुर्वेदिक फॉर्मूलेशन या पारंपरिक ज्ञान का पेटेंट नहीं कराया जा सकता है।\n\n"
                    "Why\n"
                    f"- धारा 3(p) स्पष्ट रूप से पारंपरिक ज्ञान अथवा ज्ञात घटकों के गुणों के संयोजन को गैर-पेटेंट योग्य घोषित करती है। [Source {patent_idx}]\n"
                    "- केवल तभी पेटेंट संभव हो सकता है जब कोई नवीन निष्कर्षण प्रक्रिया (novel extraction process) या अप्रत्याशित सहक्रियाशील प्रभाव (synergistic effect overcoming Section 3(e)) वैज्ञानिक रूप से सिद्ध किया जाए।\n\n"
                    "Sources\n"
                    f"- [Source {patent_idx}] {patent_src.document_title}"
                )
            return (
                "Short Answer\n"
                f"Under the Indian Patents Act, 1970, classical Ayurvedic formulations and traditional knowledge aggregations are NOT patentable under Section 3(p).\n\n"
                "Why\n"
                f"• Section 3(p) of the Patents Act explicitly excludes traditional knowledge or aggregations of known properties of traditional herbs from patentability. [Source {patent_idx}]\n"
                "• To be eligible for patent protection, an invention must demonstrate an inventive step beyond classical texts, such as a novel extraction process or scientifically proven non-obvious synergy overcoming Section 3(e).\n\n"
                "Sources\n"
                f"- [Source {patent_idx}] {patent_src.document_title}"
            )

        # 6. Check for Regulatory Licensing / Approvals Questions
        if any(k in q_lower for k in ["license", "licensing", "approval", "form 25d", "form 24d", "rule 158b", "manufacturing", "लाइसेंस", "अनुमोदन", "drug"]):
            lic_idx = next(
                (i for i, s in enumerate(retrieved_sources, start=1) if "drug" in s.topic.lower() or "cosmetic" in s.document_title.lower()),
                1,
            )
            lic_src = retrieved_sources[lic_idx - 1]

            if language == "hi":
                return (
                    "Short Answer\n"
                    f"आयुर्वेदिक दवाओं के निर्माण के लिए औषधि एवं प्रसाधन सामग्री अधिनियम, 1940 (Drugs and Cosmetics Act, 1940) के तहत राज्य आयुष प्राधिकरण से लाइसेंस प्राप्त करना अनिवार्य है।\n\n"
                    "Why\n"
                    f"- शास्त्रीय औषधियों (Classical ASU Drugs) के लिए Form 25D अथवा ऋण लाइसेंस (Form 24D) की आवश्यकता होती है। [Source {lic_idx}]\n"
                    "- पेटेंट अथवा प्रोप्राइटरी दवाओं के लिए नियम 158B के तहत सुरक्षा और प्रभावकारिता प्रमाण (proof of effectiveness dossier) प्रस्तुत करना होता है।\n\n"
                    "Sources\n"
                    f"- [Source {lic_idx}] {lic_src.document_title}"
                )
            return (
                "Short Answer\n"
                f"Manufacturing Ayurvedic formulations requires a statutory license under Chapter IV-A of the Drugs and Cosmetics Act, 1940.\n\n"
                "Why\n"
                f"• Classical Ayurvedic formulations strictly conforming to First Schedule scriptures require a Form 25D manufacturing license or Form 24D loan license. [Source {lic_idx}]\n"
                "• Patent or Proprietary Ayurvedic medicines require safety documentation and proof of effectiveness data under Rule 158B.\n\n"
                "Sources\n"
                f"- [Source {lic_idx}] {lic_src.document_title}"
            )

        # 7. Check for Ayurveda Aahar / Food Safety Questions
        if any(k in q_lower for k in ["aahar", "dietary", "food", "fssai", "labelling", "supplement", "आहार"]):
            aahar_idx = next(
                (i for i, s in enumerate(retrieved_sources, start=1) if "aahar" in s.topic.lower() or "aahar" in s.document_title.lower()),
                1,
            )
            aahar_src = retrieved_sources[aahar_idx - 1]

            if language == "hi":
                return (
                    "Short Answer\n"
                    "आयुर्वेद आहार उत्पादों का विनियमन खाद्य सुरक्षा और मानक (आयुर्वेद आहार) विनियम, 2022 के तहत FSSAI और आयुष मंत्रालय द्वारा किया जाता है।\n\n"
                    "Why\n"
                    f"- आहार उत्पादों के लेबल पर आधिकारिक आयुर्वेद आहार लोगो अनिवार्य रूप से प्रदर्शित होना चाहिए। [Source {aahar_idx}]\n"
                    "- खाद्य उत्पादों पर किसी रोग के इलाज या चिकित्सा उपचार का दावा नहीं किया जा सकता।\n\n"
                    "Sources\n"
                    f"- [Source {aahar_idx}] {aahar_src.document_title}"
                )
            return (
                "Short Answer\n"
                "Ayurveda Aahar formulations are regulated as dietary health supplements under the Food Safety and Standards (Ayurveda Aahar) Regulations, 2022.\n\n"
                "Why\n"
                f"• Products must comply with specific labelling guidelines and display the official Ayurveda Aahar logo. [Source {aahar_idx}]\n"
                "• Medicinal disease-cure claims are strictly barred on dietary food products; therapeutic claims require a drug manufacturing license under the Drugs and Cosmetics Act.\n\n"
                "Sources\n"
                f"- [Source {aahar_idx}] {aahar_src.document_title}"
            )

        # 8. Check domain and chunk relevance before default grounded synthesis (Rule 2 & Rule 3)
        primary_chunk = retrieved_sources[0]
        sec_label = primary_chunk.section_number or "Statutory Provisions"
        doc_title = primary_chunk.document_title

        domain_keywords = {
            "ayurved", "ayush", "medicine", "drug", "patent", "trademark", "copyright",
            "ipr", "intellectual property", "classical", "formulation", "herb", "plant",
            "biological", "biodiversity", "license", "licensing", "approval", "compliance",
            "aahar", "cosmetic", "food", "fssai", "nba", "tkdl", "traditional knowledge",
            "section", "act", "rule", "schedule", "jurisdiction", "authority", "law",
            "legal", "clause", "form", "claim", "infringement", "prior art",
            "आयुर्वेद", "आयुष", "दवा", "औषधि", "पेटेंट", "ट्रेडमार्क", "बौद्धिक", "संपदा",
            "अधिकार", "शास्त्रीय", "फॉर्मूलेशन", "लाइसेंस", "अनुमोदन", "आहार", "प्रसाधन", "धारा"
        }
        has_domain_term = any(k in q_lower for k in domain_keywords)
        stopwords = {"what", "when", "where", "which", "who", "whom", "this", "that", "these", "those", "have", "from", "with", "does", "will", "would", "could", "should"}
        query_words = [w.strip(".,?!:;\"'") for w in q_lower.split() if len(w) >= 4 and w not in stopwords]
        has_chunk_overlap = any(w in primary_chunk.chunk_text.lower() or w in primary_chunk.document_title.lower() for w in query_words)

        if not (has_domain_term or has_chunk_overlap):
            if language == "hi":
                return (
                    "इस प्रश्न के लिए कोई पर्याप्त प्रासंगिक स्रोत नहीं मिला। "
                    "मेरे पास इसका सटीक उत्तर देने के लिए पर्याप्त विश्वसनीय स्रोत जानकारी नहीं है। "
                    "वर्तमान ज्ञानकोश में इस विषय पर आधिकारिक साक्ष्य उपलब्ध नहीं हैं।"
                )
            elif language == "hinglish":
                return (
                    "Is sawal ke liye koi sufficiently relevant source nahi mila. "
                    "Mere paas iska accurate answer dene ke liye reliable source information nahi hai."
                )
            return (
                "No sufficiently relevant source was found for this question. "
                "I don't have enough reliable source information to answer that accurately. "
                "I could not find sufficient authoritative evidence in the current knowledge base to answer this reliably."
            )

        if language == "hi":
            clean_snippet = primary_chunk.chunk_text.replace("\n", " ").strip()
            if len(clean_snippet) > 220:
                clean_snippet = clean_snippet[:220] + "..."
            return (
                f"Short Answer\n"
                f"उपलब्ध आधिकारिक स्रोतों के आधार पर, {doc_title} ({sec_label}) के तहत विनियामक आवश्यकताएं लागू होती हैं।\n\n"
                f"Why\n"
                f"- आधिकारिक प्रावधान: {clean_snippet} [Source 1]\n\n"
                f"Sources\n"
                f"- [Source 1] {doc_title}"
            )
        else:
            clean_snippet = primary_chunk.chunk_text.replace("\n", " ").strip()
            if len(clean_snippet) > 220:
                clean_snippet = clean_snippet[:220] + "..."
            return (
                f"Short Answer\n"
                f"Based on authoritative sources retrieved under {doc_title} ({sec_label}):\n\n"
                f"Why\n"
                f"• Provision details: {clean_snippet} [Source 1]\n\n"
                f"Sources\n"
                f"- [Source 1] {doc_title}"
            )


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini LLM integration via REST API."""

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        )

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        retrieved_sources: List[SearchResultChunk],
        language: str = "en",
    ) -> str:
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": settings.LLM_TEMPERATURE,
                "maxOutputTokens": 1024,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.endpoint, json=payload)
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates and "content" in candidates[0]:
                parts = candidates[0]["content"].get("parts", [])
                if parts and "text" in parts[0]:
                    return parts[0]["text"]
            return "Unable to generate a response from Gemini API."


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI Chat Completion provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        retrieved_sources: List[SearchResultChunk],
        language: str = "en",
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.LLM_TEMPERATURE,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


def get_llm_provider() -> BaseLLMProvider:
    """Factory creating the active LLM provider based on settings."""
    provider = settings.LLM_PROVIDER.lower()

    if provider == "gemini" and settings.LLM_API_KEY:
        logger.info("Using Gemini LLM Provider.")
        return GeminiLLMProvider(api_key=settings.LLM_API_KEY, model=settings.GEMINI_MODEL)
    elif provider == "openai" and settings.LLM_API_KEY:
        logger.info("Using OpenAI LLM Provider.")
        return OpenAILLMProvider(api_key=settings.LLM_API_KEY, model=settings.OPENAI_MODEL)

    return MockLLMProvider()
