"""Schemas for Ayurvedic product regulatory and IPR classification."""

from typing import List, Optional, Union
from pydantic import BaseModel, Field


class ProductClassificationRequest(BaseModel):
    """Input payload for classifying Ayurvedic product formulations."""
    product_name: Optional[str] = Field(None, examples=["Ashwagandha Fortified Drops"])
    product_description: str = Field(
        ...,
        min_length=5,
        examples=["An aqueous extract of Ashwagandha roots fortified with synthetic piperine to increase bioavailability, intended for stress relief."]
    )
    ingredients: Optional[Union[List[str], str]] = Field(
        None, examples=[["Withania somnifera (Ashwagandha)", "Piperine"]]
    )
    formulation_information: Optional[str] = Field(
        None, examples=["Derived from Charaka Samhita formulation but modified with added active molecule."]
    )
    is_classical_text_source: Optional[bool] = Field(
        None,
        description="Whether the exact formulation and process are described in authoritative Ayurvedic texts (First Schedule of Drugs & Cosmetics Act)."
    )
    has_formulation_been_modified: Optional[bool] = Field(
        None,
        description="Whether ingredients, excipients, or preparation methods deviate from classical texts."
    )
    manufacturing_process: Optional[str] = Field(
        None, examples=["Standard aqueous-alcoholic extraction followed by crystallization."]
    )
    biological_resources_used: Optional[str] = Field(
        None, examples=["Indian wild-harvested Ashwagandha root."]
    )
    intended_use: Optional[str] = Field(
        None, examples=["Oral therapeutic dietary supplement for anxiety management."]
    )
    jurisdiction: Optional[str] = Field("India", examples=["India"])


class ProductClassificationResponse(BaseModel):
    """Structured classification result with decision support reasoning."""
    likely_category: str = Field(
        ...,
        description="Predicted regulatory category (e.g. Classical_ASU_Medicine, Patent_or_Proprietary_Medicine, Phytopharmaceutical, Ayurveda_Aahar, Cosmetic, Insufficient_Information)"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
    reasoning_summary: str = Field(..., description="Clear explanation of the legal and regulatory basis")
    missing_information: List[str] = Field(
        default_factory=list,
        description="Material questions needed to confirm or refine classification"
    )
    relevant_topics: List[str] = Field(
        default_factory=list,
        description="Legal/regulatory domains relevant to this product (e.g. AYUSH, Patent, Traditional_Knowledge, Biological_Resources)"
    )
    ipr_implications: List[str] = Field(
        default_factory=list,
        description="Immediate IPR guidance (e.g. Section 3(p) Patent bar, NBA approval requirement)"
    )
    disclaimer: str = Field(
        ...,
        description="Mandatory advisory: 'Likely classification based on provided information.'"
    )
