"""Validation helpers for jurisdictions, topics, and categories."""

from typing import Optional

SUPPORTED_JURISDICTIONS = {
    "india": "India",
    "international": "International",
    "usa": "USA",
    "european union": "European Union",
    "eu": "European Union",
    "uk": "UK",
    "japan": "Japan",
}


def normalize_jurisdiction(jurisdiction: Optional[str]) -> Optional[str]:
    """Normalizes jurisdiction string or returns canonical representation."""
    if not jurisdiction:
        return None
    key = jurisdiction.strip().lower()
    return SUPPORTED_JURISDICTIONS.get(key, jurisdiction.strip().title())


def is_valid_jurisdiction(jurisdiction: str) -> bool:
    """Checks if the jurisdiction is recognized."""
    if not jurisdiction:
        return False
    return jurisdiction.strip().lower() in SUPPORTED_JURISDICTIONS
