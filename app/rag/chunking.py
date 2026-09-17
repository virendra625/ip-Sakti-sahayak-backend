"""Structural chunking engine preserving statutory sections, headings, and pages."""

import re
from typing import List, Optional
from pydantic import BaseModel, Field

from app.utils.text_cleaner import clean_text, extract_section_and_heading


class ChunkWithMetadata(BaseModel):
    """Encapsulates a text chunk with complete source traceability."""
    chunk_index: int
    chunk_text: str
    page_number: Optional[int] = None
    section_number: Optional[str] = None
    heading: Optional[str] = None
    char_count: int = 0


def chunk_document_by_sections_or_paragraphs(
    full_text: str,
    page_number: Optional[int] = 1,
    target_chunk_size: int = 800,
    overlap_chars: int = 100,
) -> List[ChunkWithMetadata]:
    """Splits legal text into meaningful chunks while detecting and preserving

    statutory sections, clauses, and headers.
    """
    cleaned = clean_text(full_text)
    if not cleaned:
        return []

    # First, attempt to split by distinct statutory sections/rules
    section_split_pattern = r"(?=\n(?:Section\s+[0-9]+|Rule\s+[0-9]+|Chapter\s+[IVXLCDM0-9]+|Clause\s+[0-9]+))"
    raw_sections = [s.strip() for s in re.split(section_split_pattern, cleaned, flags=re.IGNORECASE) if s.strip()]

    chunks: List[ChunkWithMetadata] = []
    chunk_idx = 0
    current_active_section: Optional[str] = None
    current_active_heading: Optional[str] = None

    for raw_sec in raw_sections:
        # Check if this block defines a new section
        sec, heading = extract_section_and_heading(raw_sec)
        if sec:
            current_active_section = sec
        if heading:
            current_active_heading = heading

        # If the block fits comfortably in our chunk budget, keep it together
        if len(raw_sec) <= target_chunk_size + overlap_chars:
            chunks.append(
                ChunkWithMetadata(
                    chunk_index=chunk_idx,
                    chunk_text=raw_sec,
                    page_number=page_number,
                    section_number=current_active_section,
                    heading=current_active_heading,
                    char_count=len(raw_sec),
                )
            )
            chunk_idx += 1
        else:
            # Paragraph-based or window-based subdivision for large sections
            paragraphs = [p.strip() for p in raw_sec.split("\n\n") if p.strip()]
            buffer = ""
            for p in paragraphs:
                if len(buffer) + len(p) + 2 <= target_chunk_size:
                    buffer = f"{buffer}\n\n{p}".strip() if buffer else p
                else:
                    if buffer:
                        chunks.append(
                            ChunkWithMetadata(
                                chunk_index=chunk_idx,
                                chunk_text=buffer,
                                page_number=page_number,
                                section_number=current_active_section,
                                heading=current_active_heading,
                                char_count=len(buffer),
                            )
                        )
                        chunk_idx += 1
                    buffer = p

            if buffer:
                chunks.append(
                    ChunkWithMetadata(
                        chunk_index=chunk_idx,
                        chunk_text=buffer,
                        page_number=page_number,
                        section_number=current_active_section,
                        heading=current_active_heading,
                        char_count=len(buffer),
                    )
                )
                chunk_idx += 1

    return chunks
