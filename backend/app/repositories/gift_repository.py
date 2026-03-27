from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.models.models import Gift, Category
from app.repositories.base import BaseRepository
from app.schemas.gift import GiftFilterParams


class GiftRepository(BaseRepository[Gift]):
    def __init__(self, db: AsyncSession):
        super().__init__(Gift, db)

    async def get_with_category(self, gift_id: int) -> Optional[Gift]:
        result = await self.db.execute(
            select(Gift)
            .options(selectinload(Gift.category))
            .where(Gift.id == gift_id)
        )
        return result.scalar_one_or_none()

    async def get_all_with_filters(self, params: GiftFilterParams) -> list[Gift]:
        query = select(Gift).options(selectinload(Gift.category))
        conditions = []

        if params.occasion:
            conditions.append(Gift.occasion.ilike(params.occasion))
        if params.relationship:
            conditions.append(Gift.relationship.ilike(params.relationship))
        if params.min_price is not None:
            conditions.append(Gift.price >= params.min_price)
        if params.max_price is not None:
            conditions.append(Gift.price <= params.max_price)
        if params.category_id:
            conditions.append(Gift.category_id == params.category_id)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.offset(params.skip).limit(params.limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_gifts_without_embeddings(self) -> list[Gift]:
        result = await self.db.execute(
            select(Gift)
            .options(selectinload(Gift.category))
            .where(Gift.embedding.is_(None))
        )
        return list(result.scalars().all())

    async def get_all_gifts(self) -> list[Gift]:
        result = await self.db.execute(
            select(Gift).options(selectinload(Gift.category))
        )
        return list(result.scalars().all())

    async def get_by_product_url(self, product_url: str) -> Optional[Gift]:
        if not product_url:
            return None
        result = await self.db.execute(
            select(Gift).where(Gift.product_url == product_url)
        )
        return result.scalar_one_or_none()

    async def get_by_title(self, title: str) -> Optional[Gift]:
        if not title:
            return None
        result = await self.db.execute(
            select(Gift).where(Gift.title == title)
        )
        return result.scalar_one_or_none()

    async def update_embedding(self, gift_id: int, embedding: list[float]) -> Optional[Gift]:
        gift = await self.get_by_id(gift_id)
        if gift is None:
            return None
        gift.embedding = embedding
        await self.db.flush()
        await self.db.refresh(gift)
        return gift

    async def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        occasion: Optional[str] = None,
        relationship: Optional[str] = None,
        max_price: Optional[float] = None,
    ) -> list[Gift]:
        """
        Find gifts by vector similarity using pgvector cosine distance.
        Lower distance = more similar (cosine distance = 1 - cosine_similarity).
        """
        from pgvector.sqlalchemy import Vector
        from sqlalchemy import cast, literal

        # Build cosine distance expression
        query_vec = cast(literal(str(query_embedding)), Vector(1536))
        distance_expr = Gift.embedding.cosine_distance(query_vec)

        query = (
            select(Gift)
            .options(selectinload(Gift.category))
            .where(Gift.embedding.is_not(None))
            .order_by(distance_expr.asc())
            .limit(top_k)
        )

        conditions = [Gift.embedding.is_not(None)]
        if occasion:
            conditions.append(Gift.occasion.ilike(occasion))
        if relationship:
            conditions.append(Gift.relationship.ilike(relationship))
        if max_price is not None:
            conditions.append(Gift.price <= max_price)

        query = (
            select(Gift)
            .options(selectinload(Gift.category))
            .where(and_(*conditions))
            .order_by(distance_expr.asc())
            .limit(top_k)
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())


class CategoryRepository(BaseRepository[Category]):
    def __init__(self, db: AsyncSession):
        super().__init__(Category, db)

    async def get_by_name(self, name: str) -> Optional[Category]:
        result = await self.db.execute(
            select(Category).where(Category.name == name)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, name: str) -> tuple[Category, bool]:
        existing = await self.get_by_name(name)
        if existing:
            return existing, False
        category = Category(name=name)
        self.db.add(category)
        await self.db.flush()
        await self.db.refresh(category)
        return category, True
