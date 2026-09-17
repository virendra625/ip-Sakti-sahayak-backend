"""Utilities for text sanitization, normalization, and legal section parsing."""

import re
from typing import Optional, Tuple


def clean_text(text: str) -> str:
    """Normalizes whitespace, cleans carriage returns, and strips noise."""
    if not text:
        return ""

    # Replace windows line endings and tabs
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")

    # Remove non-printable or null control characters (keeping standard newlines)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Collapse three or more consecutive newlines into two
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse multiple inline spaces into a single space
    text = re.sub(r"[ ]{2,}", " ", text)

    return text.strip()


def extract_section_and_heading(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Identifies statutory section numbers and headings from a text block.

    Examples:
    - "Section 3(p): Inventions relating to traditional knowledge" -> ("Section 3(p)", "Inventions relating to traditional knowledge")
    - "Rule 153. Licensing of Ayurvedic drugs." -> ("Rule 153", "Licensing of Ayurvedic drugs")
    - "Chapter IV-A - Provisions relating to Ayurvedic, Siddha and Unani drugs" -> ("Chapter IV-A", "Provisions relating to Ayurvedic...")
    """
    if not text:
        return None, None

    first_line = text.strip().split("\n")[0][:150]

    # Pattern for Section / Rule / Clause / Chapter
    sec_pattern = r"^(Section\s+[0-9]+(?:\([a-zA-Z0-9]+\))*|Rule\s+[0-9]+(?:\([a-zA-Z0-9]+\))*|Clause\s+[0-9]+(?:\([a-zA-Z0-9]+\))*|Chapter\s+[IVXLCDM0-9]+(?:-[A-Z])?)"
    match = re.search(sec_pattern, first_line, re.IGNORECASE)

    if match:
        section = match.group(1).strip()
        # Remaining part of first line is heading if separated by colon, hyphen, or dot
        remainder = first_line[match.end():].strip(" :-–—.")
        heading = remainder if len(remainder) > 3 else None
        return section, heading

    # Secondary check: Header like "3(p) ..." or "[Section 3(p)]"
    sec_short = r"^\[?(?:Sec(?:tion)?\.?\s*)?([0-9]+(?:\([a-zA-Z0-9]+\))+)[\]\.\s:]"
    match_short = re.search(sec_short, first_line, re.IGNORECASE)
    if match_short:
        section = f"Section {match_short.group(1)}"
        remainder = first_line[match_short.end():].strip(" :-–—.")
        heading = remainder if len(remainder) > 3 else None
        return section, heading

    return None, None
