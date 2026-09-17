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
    }

    @classmethod
    def prepare_retrieval_query(cls, user_text: str, detected_lang: str) -> str:
        """If user asked in Hindi, augment query with corresponding English legal terms

        to maximize vector recall across authoritative English statutes.
        """
        if detected_lang != "hi":
            return user_text

        expanded_tokens = [user_text]
        for hi_word, en_trans in cls.HINDI_TO_ENGLISH_KEYWORDS.items():
            if hi_word in user_text:
                expanded_tokens.append(en_trans)

        return " ".join(expanded_tokens)

    @classmethod
    def get_localized_disclaimer(cls, language: str) -> str:
        """Returns standard legal decision-support disclaimer in requested language."""
        if language == "hi":
            return (
                "यह उत्तर केवल सूचना और निर्णय-समर्थन (decision-support) उद्देश्यों के लिए है। "
                "यह प्रणाली में उपलब्ध आधिकारिक स्रोतों पर आधारित है और इसे विधिक, चिकित्सा या "
                "नियामक सलाह नहीं माना जाना चाहिए। आधिकारिक निर्णय के लिए सक्षम विधिक विशेषज्ञ या "
                "पेटेंट अटॉर्नी से परामर्श लें।"
            )
        return (
            "This response is for informational and decision-support purposes only. "
            "It is based on the sources available in the system and should not be treated as "
            "legal, medical, regulatory, or professional advice. Verify current official requirements "
            "and consult an appropriately qualified professional for a binding decision."
        )
