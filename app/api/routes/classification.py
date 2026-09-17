"""Classification API route for Ayurvedic formulation decision-support."""

import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories.product_repository import ProductRepository
from app.schemas.classification import (
    ProductClassificationRequest,
    ProductClassificationResponse,
)
from app.services.classification_service import ClassificationService
from app.core.security import sanitize_input_text

router = APIRouter(prefix="/classification", tags=["Classification"])


@router.post(
    "",
    response_model=ProductClassificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Classify Ayurvedic Product Formulation",
    description=(
        "Analyzes formulation details to predict regulatory category (Classical ASU, "
        "Patent/Proprietary, Phytopharmaceutical, Ayurveda Aahar, or Cosmetic), identify material "
        "missing questions, and outline immediate IPR implications."
    ),
)
async def classify_product_endpoint(
    request: ProductClassificationRequest,
    db: Session = Depends(get_db),
) -> ProductClassificationResponse:
    # 1. Sanitize text
    request.product_description = sanitize_input_text(request.product_description)
    if not request.product_description:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product description cannot be empty.",
        )

    # 2. Run Classification Engine
    result = ClassificationService.classify_product(request)

    # 3. Persist product formulation record for reference
    try:
        prod_repo = ProductRepository(db)
        ingredients_str = (
            json.dumps(request.ingredients)
            if isinstance(request.ingredients, list)
            else (request.ingredients or "")
        )
        prod_repo.create(
            {
                "name": request.product_name or "Unnamed Formulation",
                "description": request.product_description,
                "category": result.likely_category,
                "classical_status": "classical" if request.is_classical_text_source else "modified/novel",
                "ingredients": ingredients_str,
                "manufacturing_process": request.manufacturing_process,
                "biological_resources": request.biological_resources_used,
            }
        )
    except Exception:
        # Persistence is non-blocking for classification
        pass

    return result
