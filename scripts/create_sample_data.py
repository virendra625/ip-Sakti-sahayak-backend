"""CLI script to populate sample products and run initial seed check.

Usage:
    python scripts/create_sample_data.py
"""

import sys
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import SessionLocal, init_db
from app.repositories.product_repository import ProductRepository
from app.repositories.document_repository import DocumentRepository


def seed_sample_products():
    """Seeds typical Ayurvedic products into database for classification and search demonstrations."""
    print("==================================================")
    print("IP-SAKTI Sahayak: Seeding Sample Products")
    print("==================================================")

    init_db()
    db = SessionLocal()
    prod_repo = ProductRepository(db)
    doc_repo = DocumentRepository(db)

    try:
        sample_products = [
            {
                "name": "Classical Chyawanprash Formulation",
                "description": "Traditional Ayurvedic polyherbal jam manufactured strictly adhering to Charaka Samhita formulae with Amla as chief ingredient.",
                "category": "Classical_ASU_Medicine",
                "classical_status": "authoritative_classical",
                "ingredients": '["Phyllanthus emblica (Amla)", "Withania somnifera", "Piper longum", "Ghee", "Honey", "Sugar"]',
                "manufacturing_process": "Traditional decoction preparation followed by paka processing in brass vessels as per Sharangadhara Samhita.",
                "biological_resources": "Wild-harvested Emblica officinalis from Madhya Pradesh forests.",
            },
            {
                "name": "Ashwa-Calm Synergistic Drops",
                "description": "Modified aqueous-alcoholic extract of Ashwagandha fortified with isolated piperine for elevated bioavailability targeting stress relief.",
                "category": "Patent_or_Proprietary_Medicine",
                "classical_status": "modified",
                "ingredients": '["Withania somnifera root extract", "Piperine 95%", "Glycerin base"]',
                "manufacturing_process": "Hydro-ethanolic extraction followed by spray-drying and micro-emulsion suspension.",
                "biological_resources": "Cultivated Withania somnifera from Rajasthan.",
            },
            {
                "name": "Ayurveda Vitality Granules",
                "description": "Ayurvedic dietary health supplement intended for nutrition and general wellness, without claiming disease mitigation.",
                "category": "Ayurveda_Aahar",
                "classical_status": "dietary_recipe",
                "ingredients": '["Roasted barley flour", "Cardamom", "Cinnamon", "Jaggery", "Dry Ginger"]',
                "manufacturing_process": "Roasting, pulverization, and dry blending.",
                "biological_resources": "Locally grown Indian agricultural produce.",
            },
        ]

        created_count = 0
        for p in sample_products:
            prod_repo.create(p)
            created_count += 1
            print(f" -> Created Product: '{p['name']}' ({p['category']})")

        doc_count = len(doc_repo.list_documents()[0])
        print(f"\nSeeding complete! Added {created_count} sample products. Documents in DB: {doc_count}")
        print("==================================================")
    finally:
        db.close()


if __name__ == "__main__":
    seed_sample_products()
