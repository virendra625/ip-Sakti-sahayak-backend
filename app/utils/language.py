"""Language utilities for multilingual routing (English, Hindi, and future Indian languages)."""

import re


def detect_language(text: str) -> str:
    """Detects whether the input text is primarily Hindi (Devanagari) or English.

    Uses Unicode block inspection (Devanagari: \u0900-\u097F).
    """
    if not text:
        return "en"

    devanagari_chars = len(re.findall(r"[\u0900-\u097F]", text))
    total_alpha = len(re.findall(r"[a-zA-Z\u0900-\u097F]", text))

    if total_alpha > 0 and (devanagari_chars / total_alpha) > 0.3:
        return "hi"

    return "en"


def get_supported_languages() -> list[dict]:
    """Returns the list of currently supported and upcoming languages."""
    return [
        {"code": "en", "name": "English", "status": "supported"},
        {"code": "hi", "name": "Hindi (हिंदी)", "status": "supported"},
        {"code": "mr", "name": "Marathi (मराठी)", "status": "planned"},
        {"code": "ta", "name": "Tamil (தமிழ்)", "status": "planned"},
    ]
