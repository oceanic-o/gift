#!/usr/bin/env python3
import asyncio
from app.core.database import AsyncSessionLocal
from app.services.rag.rag_service import RAGService

async def main():
    async with AsyncSessionLocal() as db:
        svc = RAGService()
        res = await svc.embed_and_store_gifts(db)
        print(res)

if __name__ == "__main__":
    asyncio.run(main())
