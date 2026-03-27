from fastapi import APIRouter
from app.api.v1 import auth, gifts, recommendations, rag, admin, users
from app.api.v1 import taxonomy

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(gifts.router)
api_router.include_router(gifts.category_router)
api_router.include_router(recommendations.router)
api_router.include_router(rag.router)
api_router.include_router(admin.router)
api_router.include_router(users.router)
api_router.include_router(taxonomy.router)
