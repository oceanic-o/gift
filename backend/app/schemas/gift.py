from datetime import datetime
from typing import Optional
from pydantic import BaseModel, field_validator, ConfigDict


class CategoryCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Category name cannot be empty")
        return v


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class GiftCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category_id: int
    price: float
    occasion: Optional[str] = None
    relationship: Optional[str] = None
    age_group: Optional[str] = None
    tags: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None

    @field_validator("price")
    @classmethod
    def validate_price(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 1:
            raise ValueError("Title cannot be empty")
        return v


class GiftUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[float] = None
    occasion: Optional[str] = None
    relationship: Optional[str] = None
    age_group: Optional[str] = None
    tags: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None


class GiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str]
    category_id: int
    price: float
    occasion: Optional[str]
    relationship: Optional[str]
    age_group: Optional[str] = None
    tags: Optional[str] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None
    created_at: datetime
    category: Optional[CategoryResponse] = None


class GiftFilterParams(BaseModel):
    occasion: Optional[str] = None
    relationship: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    category_id: Optional[int] = None
    skip: int = 0
    limit: int = 20
