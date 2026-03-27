import asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core.config import settings
from app.services.recommendation_service import RecommendationService
import json

async def main():
    engine = create_async_engine(settings.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://") if "postgresql+asyncpg" not in settings.DATABASE_URL else settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    
    async with session_factory() as db:
        service = RecommendationService(db)
        
        print("\n=== RUNNING HYBRID MODEL PREDICTION ===")
        print("Profile: Adult (26-40), Male, Occasion: Birthday, Relationship: Friend, Hobbies: Gaming, Tech, Budget: Under $100")
        
        try:
            # We assume user_id=1 exists or we just rely on content-based fallback for cold start
            recs = await service.get_personalized_recommendations(
                user_id=1,
                top_n=3,
                occasion="Birthday",
                relationship="Friend",
                min_price=0.0,
                max_price=100.0,
                age="Adult (26-40)",
                gender="Male",
                hobbies="gaming, technology, gadgets"
            )
            
            for i, r in enumerate(recs):
                print(f"{i+1}. {r.title} (${r.price})")
                print(f"   Score: {r.score:.3f}")
                print(f"   Category: {r.category_name}")
                print(f"   Match Details: Occasion={r.occasion}, Relationship={r.relationship}")
        except Exception as e:
            print(f"Simulation error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
