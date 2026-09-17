"""Health check endpoint for system monitoring and orchestrators."""

from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health"])


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field("healthy", description="Overall health status")
    version: str = Field(..., description="API service version")
    timestamp: str = Field(..., description="Current server time (UTC)")
    environment: str = Field(..., description="Application environment")
    components: Dict[str, str] = Field(..., description="Subsystem health statuses")


@router.get(
    "",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="System Health Status",
    description="Returns the operational status of the API and its internal services."
)
async def get_health() -> HealthResponse:
    """Performs a lightweight liveness check."""
    return HealthResponse(
        status="healthy",
        version=settings.PROJECT_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment=settings.ENVIRONMENT,
        components={
            "api": "healthy",
            "llm_provider": settings.LLM_PROVIDER,
            "embedding_provider": settings.EMBEDDING_PROVIDER,
            "database": "configured",
            "vector_store": "configured"
        }
    )
