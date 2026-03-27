"""
Gift & Category Service Layer.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.models import Gift
from app.repositories.gift_repository import GiftRepository, CategoryRepository
from app.schemas.gift import GiftCreate, GiftUpdate, GiftResponse, GiftFilterParams, CategoryCreate, CategoryResponse


class GiftService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.gift_repo = GiftRepository(db)
        self.category_repo = CategoryRepository(db)

    async def create_gift(self, payload: GiftCreate) -> GiftResponse:
        category = await self.category_repo.get_by_id(payload.category_id)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category with id={payload.category_id} not found.",
            )
        gift = Gift(
            title=payload.title,
            description=payload.description,
            category_id=payload.category_id,
            price=payload.price,
            occasion=payload.occasion,
            relationship=payload.relationship,
        )
        created = await self.gift_repo.create(gift)
        created = await self.gift_repo.get_with_category(created.id)
        logger.info("gift.created", gift_id=created.id, title=created.title)
        return GiftResponse.model_validate(created)

    async def get_gift(self, gift_id: int) -> GiftResponse:
        gift = await self.gift_repo.get_with_category(gift_id)
        if gift is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found.")
        return GiftResponse.model_validate(gift)

    async def list_gifts(self, params: GiftFilterParams) -> list[GiftResponse]:
        gifts = await self.gift_repo.get_all_with_filters(params)
        return [GiftResponse.model_validate(g) for g in gifts]

    async def update_gift(self, gift_id: int, payload: GiftUpdate) -> GiftResponse:
        gift = await self.gift_repo.get_by_id(gift_id)
        if gift is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found.")

        if payload.category_id is not None:
            category = await self.category_repo.get_by_id(payload.category_id)
            if category is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found.")

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(gift, field, value)

        await self.db.flush()
        updated = await self.gift_repo.get_with_category(gift.id)
        return GiftResponse.model_validate(updated)

    async def delete_gift(self, gift_id: int) -> None:
        deleted = await self.gift_repo.delete(gift_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gift not found.")

    async def create_category(self, payload: CategoryCreate) -> CategoryResponse:
        existing = await self.category_repo.get_by_name(payload.name)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category already exists.")
        from app.models.models import Category
        cat = Category(name=payload.name)
        created = await self.category_repo.create(cat)
        return CategoryResponse.model_validate(created)

    async def list_categories(self) -> list[CategoryResponse]:
        cats = await self.category_repo.get_all()
        return [CategoryResponse.model_validate(c) for c in cats]
