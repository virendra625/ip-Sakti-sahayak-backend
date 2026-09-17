"""Product model storing Ayurvedic formulation details for classification and IPR tracking."""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime

from app.db.database import Base


class Product(Base):
    """Ayurvedic formulation or product subjected to regulatory/IPR analysis."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)  # e.g., Classical_ASU_Medicine, Patent_or_Proprietary_Medicine
    classical_status = Column(String(100), nullable=True)  # e.g., "authoritative_classical", "modified", "novel"
    ingredients = Column(Text, nullable=True)  # JSON string or comma-separated list of ingredients
    manufacturing_process = Column(Text, nullable=True)
    biological_resources = Column(Text, nullable=True)  # e.g. details of Indian biological herbs used (NBA relevance)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Product id={self.id} name='{self.name}' category='{self.category}'>"
