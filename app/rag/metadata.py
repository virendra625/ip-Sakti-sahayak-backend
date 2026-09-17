"""Document metadata taxonomy and domain classifications for IPR & Ayurveda."""

from typing import Dict, List

DOMAINS = [
    "IPR",
    "AYUSH",
    "Traditional_Knowledge",
    "Biological_Resources",
    "International",
]

IPR_TOPICS = [
    "Patent",
    "Trademark",
    "Copyright",
    "GI",  # Geographical Indication
    "Design",
    "Trade_Secret",
    "Plant_Variety",
]

REGULATORY_TOPICS = [
    "Classical_Medicine",
    "Proprietary_Medicine",
    "New_Drug",
    "Phytopharmaceutical",
    "Ayurveda_Aahar",
    "Cosmetic",
    "Licensing",
    "Safety",
    "Efficacy",
    "Manufacturing",
    "Labelling",
]

ALL_TOPICS = sorted(list(set(IPR_TOPICS + REGULATORY_TOPICS)))

DOCUMENT_TYPES = [
    "statute",
    "regulation",
    "government_guideline",
    "treaty",
    "pharmacopoeial_standard",
    "traditional_knowledge_source",
    "official_registry",
    "research_document",
]


def get_metadata_taxonomy() -> Dict[str, List[str]]:
    """Returns the complete taxonomic metadata structure."""
    return {
        "domains": DOMAINS,
        "ipr_topics": IPR_TOPICS,
        "regulatory_topics": REGULATORY_TOPICS,
        "all_topics": ALL_TOPICS,
        "document_types": DOCUMENT_TYPES,
        "supported_jurisdictions": ["India", "International", "USA", "European Union", "UK", "Japan"],
    }
