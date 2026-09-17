"""Ayurvedic product regulatory classification and decision-support service."""

from typing import List
from app.schemas.classification import (
    ProductClassificationRequest,
    ProductClassificationResponse,
)


class ClassificationService:
    """Classifies Ayurvedic formulations into statutory regulatory categories

    (Drugs & Cosmetics Act Chapter IV-A, FSSAI Ayurveda Aahar, Phytopharmaceuticals)
    and identifies minimum clarifying questions and IPR implications.
    """

    @classmethod
    def classify_product(
        cls, request: ProductClassificationRequest
    ) -> ProductClassificationResponse:
        desc = (request.product_description or "").lower()
        formulation = (request.formulation_information or "").lower()
        intended_use = (request.intended_use or "").lower()
        process = (request.manufacturing_process or "").lower()
        bio_resources = (request.biological_resources_used or "").lower()

        missing_info: List[str] = []
        relevant_topics: List[str] = ["AYUSH"]
        ipr_implications: List[str] = []

        # 1. Identify missing material information (Section 10)
        if request.is_classical_text_source is None and "classical" not in desc and "charaka" not in formulation:
            missing_info.append(
                "Is the formulation described in an authoritative Ayurvedic text listed in the First Schedule of the Drugs and Cosmetics Act?"
            )
        if request.has_formulation_been_modified is None and "modified" not in desc and "novel" not in desc:
            missing_info.append(
                "Has the formulation been modified in ingredients, proportions, or dosage form from traditional recipes?"
            )
        if not request.intended_use:
            missing_info.append("What is the intended use (therapeutic disease treatment vs. dietary health maintenance vs. cosmetic)?")
        if not request.biological_resources_used:
            missing_info.append("Are the biological herbs or resources harvested or sourced within India?")

        # Check for Insufficient Information
        word_count = len(desc.split())
        if (
            (word_count < 5 or len(desc) < 30)
            and not request.ingredients
            and request.is_classical_text_source is None
            and not request.intended_use
        ):
            return ProductClassificationResponse(
                likely_category="Insufficient_Information",
                confidence=0.25,
                reasoning_summary=(
                    "The provided product description lacks essential technical specifics "
                    "regarding classical text adherence, ingredients, and intended use."
                ),
                missing_information=missing_info or [
                    "Please provide the ingredient list, whether it follows a classical text, and its intended use."
                ],
                relevant_topics=["AYUSH"],
                ipr_implications=[
                    "Cannot evaluate patentability or trademark viability without ingredient and process specifics."
                ],
                disclaimer=cls._get_disclaimer(),
            )

        # 2. Category Evaluation Logic
        # A. Ayurveda Aahar (FSSAI 2022 Regulations)
        is_food_or_dietary = any(
            k in intended_use or k in desc
            for k in ["food", "dietary", "aahar", "nutrition", "breakfast", "beverage", "granules", "tea"]
        )
        is_explicit_cure_claim = (
            ("cure disease" in intended_use or "treat disease" in intended_use)
            and "not for disease" not in intended_use
        )
        if is_food_or_dietary and not is_explicit_cure_claim:
            category = "Ayurveda_Aahar"
            confidence = 0.88
            reasoning = (
                "The product is intended for health and dietary consumption rather than disease treatment. "
                "Under Food Safety and Standards (Ayurveda Aahar) Regulations, 2022, it qualifies as Ayurveda Aahar, "
                "provided it does not include synthetic vitamins, minerals, or purified chemical isolates."
            )
            relevant_topics.extend(["Ayurveda_Aahar", "Safety", "Labelling"])
            ipr_implications.extend([
                "Trademarks can protect brand name and packaging.",
                "Mandatory display of the official Ayurveda Aahar logo on labels.",
                "Non-patentable as traditional food recipes under Section 3(p) unless a truly novel process is demonstrated.",
            ])

        # B. Cosmetic
        elif (
            "cosmetic" in intended_use
            or "beauty" in intended_use
            or "skin care" in intended_use
            or "hair growth" in intended_use
            or "cosmetic" in desc
        ) and "treatment" not in intended_use:
            category = "Cosmetic"
            confidence = 0.85
            reasoning = (
                "Intended for topical application for cleansing, beautifying, or altering appearance. "
                "Regulated under Cosmetic provisions of the Drugs and Cosmetics Act, requiring proof that only approved "
                "safe ingredients and colorants are utilized."
            )
            relevant_topics.extend(["Cosmetic", "Manufacturing", "Safety"])
            ipr_implications.extend([
                "Trademarks and industrial designs for packaging are key IPR assets.",
                "Novel synergistic cosmetic formulations may seek patent protection if they demonstrate unexpected properties.",
            ])

        # C. Phytopharmaceutical (CDSCO New Drug provisions)
        elif (
            "purified" in desc
            or "isolated fraction" in desc
            or "standardized fraction" in desc
            or "phytopharmaceutical" in desc
            or "bioactive molecule" in desc
        ):
            category = "Phytopharmaceutical"
            confidence = 0.82
            reasoning = (
                "Contains purified, standardized fractions of medicinal plants with defined minimum biomarkers. "
                "Under Drugs and Cosmetics Rules (Rule 122-E), phytopharmaceuticals are evaluated under New Drug provisions "
                "requiring preclinical toxicity and clinical safety/efficacy validation."
            )
            relevant_topics.extend(["New_Drug", "Phytopharmaceutical", "Safety", "Patent"])
            ipr_implications.extend([
                "High patentability potential for novel extraction processes and synergistic standardized fractions.",
                "Must overcome Section 3(d) and Section 3(p) objections by demonstrating enhanced therapeutic efficacy.",
                "Mandatory National Biodiversity Authority (NBA) approval under Section 6 of Biological Diversity Act.",
            ])

        # D. Classical ASU Medicine
        elif (
            request.is_classical_text_source is True
            or "charaka" in formulation
            or "sushruta" in formulation
            or "asava" in desc
            or "arishta" in desc
            or "bhasma" in desc
            or "taila" in desc
        ) and (request.has_formulation_been_modified is not True and "modified" not in desc):
            category = "Classical_ASU_Medicine"
            confidence = 0.90
            reasoning = (
                "Manufactured strictly in accordance with formulae described in authoritative Ayurvedic texts "
                "(First Schedule of Drugs & Cosmetics Act, 1940, Section 3(a)). "
                "Safety and efficacy are traditionally presumed for classic manufacturing."
            )
            relevant_topics.extend(["Classical_Medicine", "Licensing", "Traditional_Knowledge"])
            ipr_implications.extend([
                "Strictly NON-PATENTABLE in India under Section 3(p) of the Patents Act, 1970 (Traditional Knowledge).",
                "Monopoly rights cannot be claimed over classical ASU names; protection relies on Trademark for brand identity.",
                "Export or commercial use of biological herbs requires State Biodiversity Board (SBB) intimation.",
            ])

        # E. Patent or Proprietary ASU Medicine
        elif (
            request.has_formulation_been_modified is True
            or "modified" in desc
            or "extract" in desc
            or "synergistic" in desc
            or "drops" in desc
            or "tablet" in desc
            or "capsule" in desc
        ):
            category = "Patent_or_Proprietary_Medicine"
            confidence = 0.84
            reasoning = (
                "Contains ingredients cited in authoritative books but differs in formulation proportions, "
                "dosage format, or excipients without containing modern synthetic allopathic drugs (Section 33EEB). "
                "Requires licensing under Rule 158-B with evidence of safety."
            )
            relevant_topics.extend(["Proprietary_Medicine", "Patent", "Licensing", "Safety"])
            ipr_implications.extend([
                "Product itself is not automatically patentable if it merely aggregates known properties (Section 3(e) & 3(p)).",
                "A patent is possible ONLY if a novel, non-obvious synergistic therapeutic effect or novel delivery system is proven.",
                "Trademark registration for brand name is strongly advised.",
                "Prior NBA approval required before filing a patent if Indian biological materials are used.",
            ])

        # F. Other / New Drug
        else:
            category = "Other"
            confidence = 0.60
            reasoning = (
                "The product does not strictly fit classical ASU medicine and requires comprehensive assessment "
                "against ASU and modern pharmaceutical regulatory classifications."
            )
            relevant_topics.extend(["New_Drug", "Licensing"])
            ipr_implications.append("Seek comprehensive legal opinion to determine whether classified as an ASU or New Drug.")

        # Biological Resources check
        if bio_resources or "root" in desc or "herb" in desc or "extract" in desc:
            relevant_topics.append("Biological_Resources")
            if "Mandatory National Biodiversity Authority" not in " ".join(ipr_implications):
                ipr_implications.append(
                    "Biological Diversity Act, 2002: Commercial utilization requires intimation to the State Biodiversity Board (SBB)."
                )

        return ProductClassificationResponse(
            likely_category=category,
            confidence=round(confidence, 2),
            reasoning_summary=reasoning,
            missing_information=missing_info,
            relevant_topics=sorted(list(set(relevant_topics))),
            ipr_implications=ipr_implications,
            disclaimer=cls._get_disclaimer(),
        )

    @staticmethod
    def _get_disclaimer() -> str:
        return (
            "Likely classification based on provided information. "
            "This response is for informational and decision-support purposes only. "
            "It is based on the statutory framework of the Drugs and Cosmetics Act, 1940 and related rules, "
            "and should not be treated as an official regulatory determination. "
            "Please consult the State Licensing Authority (AYUSH) or a qualified regulatory consultant."
        )
