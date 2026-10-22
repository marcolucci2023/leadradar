from fastapi import APIRouter

from app.api.v1.routes import auth, search, leads, campaigns

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(search.router)
api_router.include_router(leads.router)
api_router.include_router(campaigns.router)