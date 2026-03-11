from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=True,
        json_encoders={
            datetime: lambda v: v.isoformat() if v else None,
            UUID: lambda v: str(v) if v else None,
        },
    )

class TimestampMixin(BaseModel):
    created_at: datetime = Field(description="Record creation timestamp")
    updated_at: datetime = Field(description="Record last update timestamp")

class IDMixin(BaseModel):
    id: UUID = Field(description="Unique identifier")

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T] = Field(description="List of items")
    total: int = Field(description="Total number of items", ge=0)
    page: int = Field(description="Current page number", ge=1)
    page_size: int = Field(description="Items per page", ge=1, le=100)
    pages: int = Field(description="Total number of pages", ge=0)
    has_next: bool = Field(description="Whether there's a next page")
    has_prev: bool = Field(description="Whether there's a previous page")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1,
        )

class SuccessResponse(BaseModel):
    success: bool = Field(default=True)
    message: str = Field(description="Success message")

class ErrorResponse(BaseModel):
    success: bool = Field(default=False)
    error: str = Field(description="Error type")
    message: str = Field(description="Error message")
    details: dict | None = Field(default=None, description="Additional error details")
