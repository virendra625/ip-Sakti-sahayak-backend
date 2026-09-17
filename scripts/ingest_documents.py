"""CLI script to ingest authoritative and sample documents into PostgreSQL and Qdrant.

Usage:
    python scripts/ingest_documents.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.db.database import SessionLocal, init_db
from app.rag.ingestion import IngestionPipeline
from app.core.logging import logger


async def ingest_sample_documents():
    """Reads all sample documents from data/documents/ and indexes them."""
    print("==================================================")
    print("IP-SAKTI Sahayak: Document Ingestion Pipeline")
    print("==================================================")

    init_db()
    db = SessionLocal()
    pipeline = IngestionPipeline(db)

    docs_dir = project_root / "data" / "documents"
    if not docs_dir.exists():
        print(f"Directory not found: {docs_dir}")
        return

    doc_configs = [
        {
            "file": "sample_patents_act_section3p.txt",
            "title": "The Patents Act, 1970 - Section 3(p) & Biological Resources",
            "authority": "Indian Patent Office (IPO) / Parliament of India",
            "jurisdiction": "India",
            "country": "India",
            "document_type": "statute",
            "topic": "Patent",
            "version": "2005_amendment",
            "source_url": "https://ipindia.gov.in",
            "description": "Statutory provisions governing non-patentability of traditional knowledge and mandatory NBA approval.",
        },
        {
            "file": "sample_drugs_and_cosmetics_act_asu.txt",
            "title": "Drugs and Cosmetics Act, 1940 - Chapter IV-A (ASU Drugs)",
            "authority": "Ministry of AYUSH / Ministry of Health",
            "jurisdiction": "India",
            "country": "India",
            "document_type": "statute",
            "topic": "Classical_Medicine",
            "version": "current",
            "source_url": "https://ayush.gov.in",
            "description": "Statutory definitions and licensing criteria for Classical ASU and Patent/Proprietary Ayurvedic medicines.",
        },
        {
            "file": "sample_ayurveda_aahar_regulations.txt",
            "title": "Food Safety and Standards (Ayurveda Aahar) Regulations, 2022",
            "authority": "Food Safety and Standards Authority of India (FSSAI) & AYUSH",
            "jurisdiction": "India",
            "country": "India",
            "document_type": "regulation",
            "topic": "Ayurveda_Aahar",
            "version": "2022_gazette",
            "source_url": "https://fssai.gov.in",
            "description": "Regulatory guidelines distinguishing Ayurveda Aahar dietary foods from Ayurvedic drugs.",
        },
        {
            "file": "sample_biological_diversity_act.txt",
            "title": "Biological Diversity Act, 2002 - Section 3 & Section 6",
            "authority": "National Biodiversity Authority (NBA)",
            "jurisdiction": "India",
            "country": "India",
            "document_type": "statute",
            "topic": "Biological_Resources",
            "version": "current",
            "source_url": "https://nbaindia.org",
            "description": "Mandatory prior approval requirements for commercial utilization and IPR filings using Indian biological herbs.",
        },
    ]

    total_ingested = 0
    total_chunks = 0

    try:
        for cfg in doc_configs:
            file_path = docs_dir / cfg["file"]
            if not file_path.exists():
                print(f"[SKIP] File not found: {file_path}")
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            print(f"\nProcessing: {cfg['title']}...")
            result = await pipeline.ingest_raw_text(
                title=cfg["title"],
                text_content=content,
                authority=cfg["authority"],
                jurisdiction=cfg["jurisdiction"],
                country=cfg["country"],
                document_type=cfg["document_type"],
                topic=cfg["topic"],
                version=cfg["version"],
                source_url=cfg["source_url"],
                description=cfg["description"],
            )

            print(f" -> Result: Document ID #{result.document_id} ({result.total_chunks} chunks indexed)")
            total_ingested += 1
            total_chunks += result.total_chunks

        print("\n==================================================")
        print(f"Ingestion Completed! Total Documents: {total_ingested}, Total Chunks: {total_chunks}")
        print("==================================================")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(ingest_sample_documents())
