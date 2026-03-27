from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import WebGift
from app.repositories.base import BaseRepository


class WebGiftRepository(BaseRepository[WebGift]):
    def __init__(self, db: AsyncSession):
        super().__init__(WebGift, db)

    async def get_by_source_url(self, source_url: str) -> Optional[WebGift]:
        if not source_url:
            return None
        result = await self.db.execute(
            select(WebGift).where(WebGift.source_url == source_url)
        )
        return result.scalar_one_or_none()

    async def get_by_gift_id(self, gift_id: int) -> Optional[WebGift]:
        result = await self.db.execute(
            select(WebGift).where(WebGift.gift_id == gift_id)
        )
        return result.scalar_one_or_none()
