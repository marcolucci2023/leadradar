from pathlib import Path
from pydantic_settings import BaseSettings

# Chemin du dossier backend (là où se trouve le .env)
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Configuration de LeadRadar — lit le fichier .env automatiquement."""

    APP_NAME: str = "LeadRadar"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Sécurité
    SECRET_KEY: str = "change-moi-en-une-chaine-aleatoire-tres-longue"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Base de données Neon PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost/leadradar"

    # IA Gemini
    GEMINI_API_KEY: str = ""
    firecrawl_api_key: str = ""
    resend_api_key: str = ""

    # Email Resend
    RESEND_API_KEY: str = ""

    # Redis Upstash
    REDIS_URL: str = "redis://localhost:6379"

    # Monitoring GlitchTip
    GLITCHTIP_DSN: str = ""

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"


settings = Settings()