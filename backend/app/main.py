from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API de génération de leads pour commerces locaux",
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclusion du routeur API v1
app.include_router(api_router)


@app.get("/")
async def root():
    """Route de test."""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "en ligne",
        "message": "Bienvenue sur LeadRadar ! 🚀",
    }


@app.get("/health")
async def health_check():
    """Route de santé pour Render."""
    return {"status": "ok"}