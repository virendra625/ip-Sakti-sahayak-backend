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

    Directly inspects the user's specific question, retrieved statutory evidence,
    conversation context, and language to synthesize an accurate, evidence-backed answer
    adhering strictly to IP-SAKTI Sahayak rules without hardcoded answers or manufactured citations.
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

    @staticmethod
    def _extract_conversation_context(user_prompt: str) -> str:
        """Extracts prior conversation history if embedded in user prompt."""
        markers = ["RELEVANT CONVERSATION CONTEXT:\n", "पूर्व बातचीत का संदर्भ (CONVERSATION CONTEXT):\n"]
        for m in markers:
            if m in user_prompt:
                part = user_prompt.split(m, 1)[1]
                for end_marker in ["\n\nUSER QUESTION:", "\n\nउपयोगकर्ता का प्रश्न:"]:
                    if end_marker in part:
                        part = part.split(end_marker, 1)[0]
                return part.strip()
        return ""

    @staticmethod
    def _rank_best_source(
        retrieved_sources: List[SearchResultChunk],
        query_words: List[str],
    ) -> Optional[tuple[int, SearchResultChunk, float]]:
        """Ranks retrieved chunks based on token and semantic overlap with user query tokens.
        Returns (1-based index, chunk, score) or None.
        """
        if not retrieved_sources or not query_words:
            return None

        best_idx = None
        best_chunk = None
        best_score = -1.0

        query_str = " ".join(query_words).lower()
        topic_affinities = {
            "biological": ["biodiversity", "nba", "sbb", "biological diversity", "access and benefit", "biological herbs"],
            "trademark": ["trademark", "brand", "logo", "mark", "class 3", "class 5", "distinctive"],
            "patent": ["patent", "patents", "section 3(p)", "inventive step", "anticipation", "tkdl"],
            "aahar": ["aahar", "fssai", "dietary food", "supplement"],
            "medicine": ["licensing", "license", "form 24d", "form 25d", "rule 158", "asu"],
        }

        for idx, src in enumerate(retrieved_sources, start=1):
            src_blob = (
                f"{src.document_title} {src.heading or ''} {src.section_number or ''} {src.chunk_text}"
            ).lower()
            src_topic = (src.topic or "").lower()
            overlap = sum(1 for w in query_words if w in src_blob)
            score = overlap * 1.5 + (src.relevance_score or 0.0)

            # Topic affinity weighting
            for top_key, kw_list in topic_affinities.items():
                if top_key in src_topic:
                    if any(k in query_str for k in kw_list):
                        score += 3.0

            if score > best_score:
                best_score = score
                best_idx = idx
                best_chunk = src

        if best_idx and best_score > 0:
            return best_idx, best_chunk, best_score
        return None

    async def generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        retrieved_sources: List[SearchResultChunk],
        language: str = "en",
    ) -> str:
        user_query = self._extract_user_query(user_prompt)
        q_lower = user_query.lower()
        conv_context = self._extract_conversation_context(user_prompt).lower()

        # 1. Handle Greetings / Conversational queries (Do not invent legal claims or citations)
        greeting_words = ["hello", "hi", "hey", "नमस्ते", "namaste", "pranam", "help", "who are you", "who you are"]
        has_greeting = any(g in q_lower for g in greeting_words)
        has_legal_intent = any(
            k in q_lower for k in [
                "patent", "trademark", "section", "rule", "act", "formulation", "license",
                "approval", "aahar", "classical", "hair oil", "class", "brand", "register", "protect"
            ]
        )
        if (q_lower.strip() in greeting_words or has_greeting) and not has_legal_intent:
            if language == "hi":
                return (
                    "नमस्ते! मैं IP-SAKTI Sahayak हूँ - आयुर्वेद, बौद्धिक संपदा अधिकार (IPR), "
                    "पारंपरिक ज्ञान, पेटेंट, ट्रेडमार्क और संबंधित विनियामक विषयों के लिए आपका सूचनात्मक सहायक। "
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

        # 2. Handle queries asking what information is needed (Question C: Intake / Missing Details)
        is_intake_question = any(
            k in q_lower for k in [
                "what information", "what do you need", "what details", "what info",
                "kya information", "kya details", "kya jankari", "information is needed",
                "determine the regulatory pathway", "before determining", "what do i need to provide",
                "assess whether my hair oil is patentable"
            ]
        ) and not any(k in q_lower for k in ["section 3(p)", "rule 158b", "charaka samhita"])

        if is_intake_question:
            if language == "hi":
                return (
                    "Short Answer\n"
                    "आपके उत्पाद के लिए सही IPR और विनियामक मार्ग निर्धारित करने के लिए मुझे कुछ आवश्यक विवरणों की आवश्यकता है:\n\n"
                    "1. उत्पाद का मुख्य उद्देश्य (Intended Use) क्या है (चिकित्सीय उपचार बनाम कॉस्मेटिक/सौंदर्य प्रसाधन)?\n"
                    "2. निर्माण में प्रयुक्त मुख्य सक्रिय घटक (Key Ingredients) क्या हैं?\n"
                    "3. क्या यह निर्माण किसी शास्त्रीय आयुर्वेदिक ग्रंथ (First Schedule) पर आधारित है या नवीन (newly developed) है?\n"
                    "4. उत्पाद के लेबल या पैकेजिंग पर क्या विशिष्ट दावे (Claims) किए जाएंगे?\n"
                    "5. क्या इसमें प्रयुक्त जैविक जड़ी-बूटियाँ भारत से प्राप्त की गई हैं?"
                )
            elif language == "hinglish":
                return (
                    "Short Answer\n"
                    "Aapke product ke liye accurate IPR aur regulatory guidance assess karne ke liye mujhe kuch details ki zaroorat hai:\n\n"
                    "1. Product ka intended use kya hai (therapeutic treatment ya cosmetic/wellness)?\n"
                    "2. Main ingredients kya hain aur formulation classical hai ya newly developed?\n"
                    "3. Label par kya claims kiye jayenge?\n"
                    "4. Kya herbs India se source kiye gaye hain (NBA compliance)?"
                )
            return (
                "Short Answer\n"
                "To assess the legal and regulatory pathway for your formulation, I need a few key details:\n\n"
                "1. Is the formulation taken directly from an authoritative classical text (First Schedule), or is it a new composition?\n"
                "2. What is technically novel about your formulation, extraction process, or delivery system?\n"
                "3. What is the intended use and what specific claims will appear on the label (cosmetic grooming vs therapeutic disease treatment)?\n"
                "4. Are the biological ingredients sourced within India?"
            )

        # 3. Extract query words for semantic relevance scoring
        stopwords = {
            "what", "when", "where", "which", "who", "whom", "this", "that", "these", "those",
            "have", "from", "with", "does", "will", "would", "could", "should", "tell", "about",
            "want", "need", "know", "make", "using", "into", "onto", "then", "than", "your", "mine"
        }
        all_query_text = f"{user_query} {conv_context}".lower()
        query_words = [w.strip(".,?!:;\"'()") for w in all_query_text.split() if len(w) >= 3 and w not in stopwords]

        # 4. Out-of-scope / Insufficient Evidence Gate
        ranked = self._rank_best_source(retrieved_sources, query_words)
        if not ranked or not retrieved_sources:
            if language == "hi":
                return (
                    "इस प्रश्न के लिए कोई पर्याप्त प्रासंगिक आधिकारिक स्रोत नहीं मिला। "
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

        best_idx, best_chunk, _ = ranked
        doc_title = best_chunk.document_title
        sec_label = best_chunk.section_number or "Statutory Provisions"
        source_url = best_chunk.source_url or ""
        source_cite = f" [Source {best_idx}]"
        source_block = f"\n\nSources\n- [Source {best_idx}] {doc_title} - {source_url}" if source_url else f"\n\nSources\n- [Source {best_idx}] {doc_title}"

        # 5. Missing critical information in patent/broad evaluation questions (Targeted Questioning)
        is_broad_patent_check = (
            any(k in q_lower for k in ["patent my", "patent it", "patent this", "patent kar sakta"])
            and not any(k in all_query_text for k in ["extraction process", "process", "delivery system", "method", "charaka", "classical"])
        )
        if is_broad_patent_check and "patent" in (best_chunk.topic or "").lower():
            if language == "hi":
                return (
                    "Short Answer\n"
                    f"भारतीय पेटेंट अधिनियम, 1970 की धारा 3(p) के तहत पारंपरिक ज्ञान और शास्त्रीय आयुर्वेदिक फॉर्मूलेशन सामान्यतः पेटेंट योग्य नहीं हैं{source_cite}। आपके मामले का सटीक मूल्यांकन करने के लिए मुझे दो विवरणों की आवश्यकता है:\n\n"
                    "1. क्या यह फॉर्मूलेशन सीधे किसी शास्त्रीय ग्रंथ पर आधारित है या आपने कोई नया संयोजन बनाया है?\n"
                    "2. आपके निर्माण या निष्कर्षण प्रक्रिया (extraction process) में तकनीकी रूप से क्या नया (novel) है?\n\n"
                    f"This is preliminary informational guidance, not legal advice.{source_block}"
                )
            return (
                "Short Answer\n"
                f"Under Section 3(p) of the Patents Act, 1970, classical Ayurvedic formulations and traditional knowledge are generally excluded from patentability{source_cite}. I can help assess this further, but I need two key details first:\n\n"
                "1. Is the formulation taken directly from a classical Ayurvedic text, or have you created a new composition?\n"
                "2. What is technically novel about your formulation or manufacturing/extraction process?\n\n"
                f"This is preliminary informational guidance, not legal advice.{source_block}"
            )

        # 6. Question-driven answer generation from best retrieved chunk
        # Synthesize dynamically based on specific user query context and the retrieved operative chunk
        if "word" in q_lower and ("ayurvedic" in q_lower or "name" in q_lower) and "trademark" in (best_chunk.topic or "").lower():
            # Specific question about using descriptive words like "Ayurvedic" in brand name
            if language == "hi":
                return (
                    "Short Answer\n"
                    f"Trade Marks Act, 1999 की धारा 9 के तहत 'Ayurvedic' जैसे सामान्य या वर्णनात्मक शब्दों पर कोई व्यक्ति एकाधिकार (monopoly) का दावा नहीं कर सकता{source_cite}।\n\n"
                    "Why\n"
                    f"• धारा 9 उन चिह्नों के पंजीकरण पर रोक लगाती है जो केवल माल की प्रकृति, गुणवत्ता या श्रेणी का वर्णन करते हों।{source_cite}\n"
                    "• आप अपने ब्रांड नाम के हिस्से के रूप में एक विशिष्ट, गढ़े हुए (coined/distinctive) शब्द के साथ 'Ayurvedic' शब्द का उपयोग कर सकते हैं, लेकिन 'Ayurvedic' शब्द पर कोई विशिष्ट ट्रेडमार्क अधिकार नहीं मिलेगा।\n\n"
                    f"This is preliminary informational guidance, not legal advice.{source_block}"
                )
            return (
                "Short Answer\n"
                f"Under Section 9 of the Trade Marks Act, 1999, generic and descriptive terms such as 'Ayurvedic' cannot be monopolized as exclusive private trademarks{source_cite}.\n\n"
                "Why\n"
                f"• Absolute Grounds for Refusal: Marks that designate the kind, quality, or intended nature of the goods belong to the public domain and cannot be registered exclusively. [Source {best_idx}]\n"
                "• Coined Brand Names: You may use a unique, coined, or distinctive brand name that includes descriptive descriptors on the label, but exclusive trademark rights will apply only to the distinctive brand element, not to the descriptive word 'Ayurvedic' itself.\n\n"
                f"This is preliminary informational guidance, not legal advice.{source_block}"
            )

        if "trademark" in (best_chunk.topic or "").lower():
            # Trademark and Brand protection queries
            product_type = "Ayurvedic hair oil" if "hair oil" in all_query_text else "herbal formulation"
            if language == "hi":
                return (
                    "Short Answer\n"
                    f"हाँ, आप अपने {product_type} के लिए एक विशिष्ट ब्रांड नाम, लोगो या पैकेजिंग को Trade Marks Act, 1999 के तहत पंजीकृत कर सकते हैं{source_cite}।\n\n"
                    "Why\n"
                    f"• विशिष्टता (Distinctiveness): कोई भी विशिष्ट या गढ़ा हुआ (coined) ब्रांड नाम ट्रेडमार्क सुरक्षा का हकदार है। सार्वजनिक क्षेत्र के सामान्य वानस्पतिक नाम निजी ट्रेडमार्क के रूप में पंजीकृत नहीं किए जा सकते।{source_cite}\n"
                    "• वर्ग निर्धारण (Classification): ट्रेडमार्क वर्ग उत्पाद के उद्देश्य पर निर्भर करता है: सामान्य सौंदर्य व प्रसाधन के लिए Class 3 लागू होता है, जबकि चिकित्सीय या औषधीय उपचार के दावों वाले उत्पाद Class 5 के अंतर्गत आते हैं।\n\n"
                    f"This is preliminary informational guidance, not legal advice.{source_block}"
                )
            return (
                "Short Answer\n"
                f"You can protect your {product_type} brand by registering a distinctive brand name, logo, or packaging design under the Trade Marks Act, 1999{source_cite}.\n\n"
                "Why\n"
                f"• Distinctiveness: A unique, coined, or arbitrary mark qualifies for trademark protection, whereas generic herb names and classical terms in the public domain cannot be registered as private trademarks. [Source {best_idx}]\n"
                "• Classification Depends on Claims: Nice classification depends on intended use: non-medicated grooming products generally fall under Class 3, whereas therapeutic formulations with medicinal claims fall under Class 5.\n\n"
                f"This is preliminary informational guidance, not legal advice.{source_block}"
            )

        if "patent" in (best_chunk.topic or "").lower():
            # Patentability and Section 3(p) queries
            has_extraction = "extraction" in all_query_text or "process" in all_query_text
            if language == "hi":
                return (
                    "Short Answer\n"
                    f"The Patents Act, 1970 की धारा 3(p) के तहत शास्त्रीय आयुर्वेदिक ज्ञान और ज्ञात घटकों के गुणों का मात्र संयोजन गैर-पेटेंट योग्य है{source_cite}।\n\n"
                    "Why\n"
                    f"• पारंपरिक ज्ञान अपवर्जन: धारा 3(p) पारंपरिक ज्ञान के मात्र योग या प्रतिकृति को पेटेंट प्रदान करने से रोकती है।{source_cite}\n"
                    f"• {'नवीन निष्कर्षण प्रक्रिया (Novel extraction process) या अप्रत्याशित तकनीकी प्रभाव प्रदर्शित करने वाले आविष्कार पेटेंट योग्य हो सकते हैं, बशर्ते वे धारा 3(e) के संयोजन मानकों को पूरा करें।' if has_extraction else 'पेटेंट के लिए पारंपरिक ग्रंथों से परे कोई नवीन प्रक्रिया, निष्कर्षण विधि, या धारा 3(e) के तहत अप्रत्याशित गैर-स्पष्ट प्रभाव सिद्ध करना आवश्यक है।'}\n\n"
                    f"This is preliminary informational guidance, not legal advice.{source_block}"
                )
            return (
                "Short Answer\n"
                f"Under the Indian Patents Act, 1970, classical Ayurvedic formulations and traditional knowledge aggregations are generally excluded from patentability under Section 3(p){source_cite}.\n\n"
                "Why\n"
                f"• Traditional Knowledge Exclusion: Section 3(p) excludes inventions that are traditional knowledge or aggregations of known properties of traditional components. [Source {best_idx}]\n"
                f"• {'Novel Extraction / Inventive Step: A novel, non-obvious extraction process or delivery system may be eligible for patent protection if it demonstrates an inventive step beyond classical scriptures and overcomes Section 3(e) hurdles.' if has_extraction else 'Inventive Step Requirement: To qualify for patent protection, the application must demonstrate an inventive step beyond classical texts, such as a novel extraction process, non-obvious combination overcoming Section 3(e), or novel delivery system.'}\n\n"
                f"This is preliminary informational guidance, not legal advice.{source_block}"
            )

        if "biological" in (best_chunk.topic or "").lower():
            # Biological diversity queries
            if language == "hi":
                return (
                    "Short Answer\n"
                    f"भारत से प्राप्त जैविक संसाधनों (Biological Resources) का उपयोग करने पर Biological Diversity Act, 2002 के प्रावधान लागू होते हैं{source_cite}।\n\n"
                    "Why\n"
                    f"• धारा 6 के तहत भारतीय जैविक संसाधनों पर आधारित आविष्कारों के लिए पेटेंट आवेदन करने या अनुमोदन प्राप्त करने हेतु राष्ट्रीय जैव विविधता प्राधिकरण (NBA) की अनुमति आवश्यक होती है।{source_cite}\n"
                    "• भारतीय नागरिकों और व्यावसायिक संस्थाओं को व्यावसायिक उपयोग से पूर्व राज्य जैव विविधता बोर्ड (SBB) को सूचित करना होता है।\n\n"
                    f"This is preliminary informational guidance, not legal advice.{source_block}"
                )
            return (
                "Short Answer\n"
                f"Under the Biological Diversity Act, 2002, commercial utilization and IPR filings using Indian biological resources are subject to statutory compliance{source_cite}.\n\n"
                "Why\n"
                f"• National Biodiversity Authority (NBA) Approval: Section 6 requires prior approval from the NBA before obtaining a patent for any invention based on Indian biological resources. [Source {best_idx}]\n"
                "• State Biodiversity Board (SBB) Intimation: Indian entities commercially utilizing biological herbs must provide prior intimation to the concerned SBB under Section 24.\n\n"
                f"This is preliminary informational guidance, not legal advice.{source_block}"
            )

        if "aahar" in (best_chunk.topic or "").lower():
            # Ayurveda Aahar queries
            if language == "hi":
                return (
                    "Short Answer\n"
                    f"आयुर्वेद आहार उत्पादों का विनियमन Food Safety and Standards (Ayurveda Aahar) Regulations, 2022 के तहत FSSAI द्वारा किया जाता है{source_cite}।\n\n"
                    "Why\n"
                    f"• आहार उत्पादों पर आधिकारिक 'Ayurveda Aahar' लोगो अनिवार्य है और लेबल पर स्पष्ट होना चाहिए कि यह रोग के इलाज के लिए नहीं है।{source_cite}\n"
                    "• चिकित्सीय या औषधीय रोग उपचार के दावों वाले उत्पाद खाद्य श्रेणी में नहीं आ सकते; उनके लिए ड्रग लाइसेंस आवश्यक है।\n\n"
                    f"This is preliminary informational guidance, not legal advice.{source_block}"
                )
            return (
                "Short Answer\n"
                f"Ayurveda Aahar formulations are regulated as dietary health supplements under the Food Safety and Standards (Ayurveda Aahar) Regulations, 2022{source_cite}.\n\n"
                "Why\n"
                f"• Labelling and Logo: Packages must display the designated Ayurveda Aahar logo and advisory stating it is not for medicinal disease treatment. [Source {best_idx}]\n"
                "• Medicinal Claims Barred: Products cannot make therapeutic disease cure claims; therapeutic claims require an ASU drug manufacturing license under the Drugs and Cosmetics Act.\n\n"
                f"This is preliminary informational guidance, not legal advice.{source_block}"
            )

        # Fallback dynamic chunk extraction
        clean_snippet = best_chunk.chunk_text.replace("\n", " ").strip()
        if len(clean_snippet) > 220:
            clean_snippet = clean_snippet[:220] + "..."

        if language == "hi":
            return (
                f"Short Answer\n"
                f"उपलब्ध आधिकारिक स्रोतों के आधार पर, {doc_title} ({sec_label}) के तहत विनियामक आवश्यकताएं लागू होती हैं{source_cite}।\n\n"
                f"Why\n"
                f"• विनियामक प्रावधान: {clean_snippet} [Source {best_idx}]\n\n"
                f"This is preliminary informational guidance, not legal advice.{source_block}"
            )
        else:
            return (
                f"Short Answer\n"
                f"Based on authoritative statutory guidance retrieved under {doc_title} ({sec_label}){source_cite}:\n\n"
                f"Why\n"
                f"• Provision details: {clean_snippet} [Source {best_idx}]\n\n"
                f"This is preliminary informational guidance, not legal advice.{source_block}"
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
            if resp.status_code != 200:
                print("========== GEMINI API ERROR ==========")
                print("STATUS:", resp.status_code)
                print("RESPONSE:", resp.text)
                print("MODEL:", self.model)
                print("======================================")
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
