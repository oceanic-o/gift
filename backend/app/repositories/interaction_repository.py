from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.models.models import Interaction, Recommendation, ModelMetric, RAGQuery, InteractionType
from app.repositories.base import BaseRepository


class InteractionRepository(BaseRepository[Interaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(Interaction, db)

    async def get_user_interactions(
        self, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[Interaction]:
        result = await self.db.execute(
            select(Interaction)
            .where(Interaction.user_id == user_id)
            .order_by(Interaction.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_interactions_for_matrix(self) -> list[Interaction]:
        """Get all interactions for building the user-item matrix."""
        result = await self.db.execute(
            select(Interaction).order_by(Interaction.user_id, Interaction.gift_id)
        )
        return list(result.scalars().all())

    async def get_interaction_counts_by_type(self) -> dict[str, int]:
        result = await self.db.execute(
            select(Interaction.interaction_type, func.count(Interaction.id))
            .group_by(Interaction.interaction_type)
        )
        rows = result.all()
        return {str(row[0].value): row[1] for row in rows}

    async def user_has_interaction(self, user_id: int, gift_id: int) -> bool:
        result = await self.db.execute(
            select(Interaction.id).where(
                and_(Interaction.user_id == user_id, Interaction.gift_id == gift_id)
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_total_count(self) -> int:
        result = await self.db.execute(
            select(func.count(Interaction.id))
        )
        return result.scalar_one()

    async def get_all_paginated(self, skip: int = 0, limit: int = 100) -> list[Interaction]:
        result = await self.db.execute(
            select(Interaction)
            .options(selectinload(Interaction.user), selectinload(Interaction.gift))
            .order_by(Interaction.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


class RecommendationRepository(BaseRepository[Recommendation]):
    def __init__(self, db: AsyncSession):
        super().__init__(Recommendation, db)

    async def get_user_recommendations(
        self, user_id: int, limit: int = 10
    ) -> list[Recommendation]:
        result = await self.db.execute(
            select(Recommendation)
            .options(selectinload(Recommendation.gift).selectinload(Recommendation.gift.property.mapper.class_.category))
            .where(Recommendation.user_id == user_id)
            .order_by(Recommendation.score.desc(), Recommendation.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_user_recommendations(self, user_id: int) -> int:
        """Remove old recommendations for a user before re-generating."""
        result = await self.db.execute(
            select(Recommendation).where(Recommendation.user_id == user_id)
        )
        recs = result.scalars().all()
        for r in recs:
            await self.db.delete(r)
        await self.db.flush()
        return len(recs)

    async def bulk_create(self, recommendations: list[Recommendation]) -> list[Recommendation]:
        self.db.add_all(recommendations)
        await self.db.flush()
        return recommendations

    async def get_total_count(self) -> int:
        result = await self.db.execute(select(func.count(Recommendation.id)))
        return result.scalar_one()


class ModelMetricRepository(BaseRepository[ModelMetric]):
    def __init__(self, db: AsyncSession):
        super().__init__(ModelMetric, db)

    async def get_latest_by_model(self, model_name: str) -> Optional[ModelMetric]:
        result = await self.db.execute(
            select(ModelMetric)
            .where(ModelMetric.model_name == model_name)
            .order_by(ModelMetric.evaluated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_best_model(self) -> Optional[ModelMetric]:
        result = await self.db.execute(
            select(ModelMetric).order_by(ModelMetric.f1_score.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_all_metrics(self) -> list[ModelMetric]:
        result = await self.db.execute(
            select(ModelMetric).order_by(ModelMetric.evaluated_at.desc())
        )
        return list(result.scalars().all())


class RAGQueryRepository(BaseRepository[RAGQuery]):
    def __init__(self, db: AsyncSession):
        super().__init__(RAGQuery, db)

    async def get_user_queries(self, user_id: int, limit: int = 20) -> list[RAGQuery]:
        result = await self.db.execute(
            select(RAGQuery)
            .where(RAGQuery.user_id == user_id)
            .order_by(RAGQuery.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
