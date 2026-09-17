"""Common schemas and response models for IP-SAKTI Sahayak."""

from typing import Generic, Optional, TypeVar, Any
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ErrorDetail(BaseModel):
    """Structured error payload format."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation of the error")
    details: Optional[Any] = Field(None, description="Optional supporting contextual details")


class StandardResponse(BaseModel, Generic[DataT]):
    """Standard unified response envelope."""
    success: bool = Field(True, description="Indicates if the request succeeded")
    data: Optional[DataT] = Field(None, description="Response payload")
    error: Optional[ErrorDetail] = Field(None, description="Populated when success is false")


class PaginationParams(BaseModel):
    """Query parameters for paginated endpoints."""
    skip: int = Field(0, ge=0, description="Offset records count")
    limit: int = Field(20, ge=1, le=100, description="Maximum records to return")
