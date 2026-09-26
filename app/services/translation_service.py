"""Multilingual processing service preserving authoritative source integrity."""

from typing import Dict, Any, List
from app.utils.language import detect_language


class TranslationService:
    """Handles multilingual query parsing and synthesis while preserving

    unaltered English citations for legal accuracy.
    """

    # Common Ayurvedic Hindi-English keyword bridges for cross-lingual vector matching
    HINDI_TO_ENGLISH_KEYWORDS = {
        "पेटेंट": "patent",
        "आयुर्वेद": "ayurveda",
        "शास्त्रीय": "classical formulation",
        "दवा": "drug medicine",
        "लाइसेंस": "licensing",
        "अधिकार": "intellectual property rights IPR",
        "पारंपरिक ज्ञान": "traditional knowledge TKDL",
        "जैव विविधता": "biological diversity biological resources",
        "आहार": "ayurveda aahar food safety",
        "अधिनियम": "act statute",
        "धारा": "section",
        "प्रसाधन": "cosmetic",
        "ट्रेडमार्क": "trademark class",
        "ब्रांड": "brand trademark",
        "परीक्षण": "testing clinical trials safety",
        "अनुमोदन": "approval regulatory license",
    }

    @classmethod
    def prepare_retrieval_query(cls, user_text: str, detected_lang: str) -> str:
        """Augments query with relevant statutory and multilingual keywords
        to maximize vector recall across authoritative statutory provisions.
        """
        expanded_tokens = [user_text]

        # 1. Multilingual Hindi/Hinglish bridge
        if detected_lang in ("hi", "hinglish"):
            for hi_word, en_trans in cls.HINDI_TO_ENGLISH_KEYWORDS.items():
                if hi_word in user_text:
                    expanded_tokens.append(en_trans)

        # 2. Domain term enrichment for short queries across English and Hindi
        lower_q = user_text.lower()
        if any(k in lower_q for k in ("patent", "पेटेंट")) and any(k in lower_q for k in ("classical", "शास्त्रीय", "traditional", "पारंपरिक", "ayurved", "आयुर्वेद", "medicine", "दवा")):
            expanded_tokens.append("traditional knowledge section 3")
        if any(k in lower_q for k in ("trademark", "ट्रेडमार्क", "brand", "ब्रांड", "logo")):
            expanded_tokens.append("trademark classification distinctiveness")
        if any(k in lower_q for k in ("aahar", "आहार", "dietary food")):
            expanded_tokens.append("ayurveda aahar food safety regulations")
        if any(k in lower_q for k in ("license", "लाइसेंस", "manufacturing approval", "अनुमोदन", "rule 158")):
            expanded_tokens.append("drugs and cosmetics licensing ASU")
        if any(k in lower_q for k in ("biodiversity", "जैव विविधता", "nba", "biological diversity", "biological resource")):
            expanded_tokens.append("biological diversity act approval commercial utilization")

        return " ".join(expanded_tokens)

    @classmethod
    def get_localized_disclaimer(cls, language: str) -> str:
        """Returns standard legal decision-support disclaimer in requested language."""
        if language == "hi":
            return (
                "यह केवल प्रारंभिक सूचनात्मक मार्गदर्शन एवं निर्णय-समर्थन है, कानूनी सलाह नहीं। "
                "व्यावसायिक उपयोग से पहले कृपया संबंधित प्राधिकरण या योग्य पेशेवर से लागू आवश्यकताओं का सत्यापन करें।"
            )
        return (
            "This is preliminary informational guidance, not legal advice. "
            "Please verify the applicable requirements with the relevant authority or a qualified professional before commercial use."
        )
