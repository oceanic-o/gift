from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator


class UserProfileBase(BaseModel):
    age: Optional[str] = None
    gender: Optional[str] = None
    hobbies: Optional[str] = None
    relationship: Optional[str] = None
    occasion: Optional[str] = None
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    favorite_categories: Optional[list[str]] = None
    occasions: Optional[list[str]] = None
    gifting_for_ages: Optional[list[str]] = None
    interests: Optional[list[str]] = None

    @field_validator("budget_min", "budget_max")
    @classmethod
    def validate_budget(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if v < 0:
            raise ValueError("Budget must be non-negative")
        return v


class UserProfileUpdate(UserProfileBase):
    pass


class UserPreferencesUpdate(UserProfileBase):
    pass


class UserProfileResponse(UserProfileBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    updated_at: datetime


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str


class PublicReviewResponse(BaseModel):
    name: str
    role: str
    avatar: str
    rating: int
    review: str
    reviewed_at: datetime
