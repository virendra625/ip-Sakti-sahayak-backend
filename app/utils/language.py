"""Language utilities for multilingual routing (English, Hindi, and future Indian languages)."""

import re


HINGLISH_MARKERS = {
    "kya", "hai", "hain", "kaise", "hoga", "hogi", "kar", "sakta", "sakte", "sakti",
    "hoon", "hu", "ke", "liye", "mera", "meri", "mere", "chahiye", "kaun", "bhi",
    "aur", "mein", "dawa", "aushadhi", "bana", "raha", "rahi", "ayurvedic", "lagta"
}


def detect_language(text: str) -> str:
    """Detects whether input text is Hindi (Devanagari), Hinglish, or English."""
    if not text:
        return "en"

    devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
    total_alpha = len(re.findall(r"[a-zA-Z\u0900-\u097F]", text))

    if total_alpha > 0 and (devanagari_chars / total_alpha) > 0.3:
        return "hi"

    # Check for conversational Hinglish in Latin script
    words = {w.strip(".,?!:;\"'") for w in text.lower().split()}
    matching_hinglish = words.intersection(HINGLISH_MARKERS)
    if len(matching_hinglish) >= 2:
        return "hinglish"

    return "en"


def get_supported_languages() -> list[dict]:
    """Returns the list of currently supported and upcoming languages."""
    return [
        {"code": "en", "name": "English", "status": "supported"},
        {"code": "hi", "name": "Hindi (हिंदी)", "status": "supported"},
        {"code": "mr", "name": "Marathi (मराठी)", "status": "planned"},
        {"code": "ta", "name": "Tamil (தமிழ்)", "status": "planned"},
    ]
