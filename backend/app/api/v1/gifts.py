from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_current_admin
from app.schemas.gift import (
    GiftCreate, GiftUpdate, GiftResponse, GiftFilterParams,
    CategoryCreate, CategoryResponse
)
from app.services.gift_service import GiftService

router = APIRouter(prefix="/gifts", tags=["Gifts"])
category_router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=list[GiftResponse])
async def list_gifts(
    occasion: str = Query(None),
    relationship: str = Query(None),
    min_price: float = Query(None, ge=0),
    max_price: float = Query(None, ge=0),
    category_id: int = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List gifts with optional filtering."""
    params = GiftFilterParams(
        occasion=occasion,
        relationship=relationship,
        min_price=min_price,
        max_price=max_price,
        category_id=category_id,
        skip=skip,
        limit=limit,
    )
    service = GiftService(db)
    return await service.list_gifts(params)


@router.get("/{gift_id}", response_model=GiftResponse)
async def get_gift(gift_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single gift by ID."""
    service = GiftService(db)
    return await service.get_gift(gift_id)


@router.post("/", response_model=GiftResponse, status_code=201)
async def create_gift(
    payload: GiftCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    """Create a new gift (admin only)."""
    service = GiftService(db)
    return await service.create_gift(payload)


@router.put("/{gift_id}", response_model=GiftResponse)
async def update_gift(
    gift_id: int,
    payload: GiftUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    """Update an existing gift (admin only)."""
    service = GiftService(db)
    return await service.update_gift(gift_id, payload)


@router.delete("/{gift_id}", status_code=204)
async def delete_gift(
    gift_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    """Delete a gift (admin only)."""
    service = GiftService(db)
    await service.delete_gift(gift_id)


@category_router.get("/", response_model=list[CategoryResponse])
async def list_categories(db: AsyncSession = Depends(get_db)):
    """List all categories."""
    service = GiftService(db)
    return await service.list_categories()


@category_router.post("/", response_model=CategoryResponse, status_code=201)
async def create_category(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(get_current_admin),
):
    """Create a new category (admin only)."""
    service = GiftService(db)
    return await service.create_category(payload)
