"""Repository for storing and querying product formulations."""

from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.product import Product


class ProductRepository:
    """Provides methods to persist and retrieve Ayurvedic products."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, product_data: dict) -> Product:
        """Saves a product formulation."""
        product = Product(**product_data)
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product

    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Fetches a product by ID."""
        return self.db.query(Product).filter(Product.id == product_id).first()

    def list_products(self, limit: int = 50) -> List[Product]:
        """Lists saved products."""
        return self.db.query(Product).order_by(Product.id.desc()).limit(limit).all()
