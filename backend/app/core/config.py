import os

class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./leadradar.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    firecrawl_api_key: str = os.getenv("FIRECRAWL_API_KEY", "")
    resend_api_key: str = os.getenv("RESEND_API_KEY", "")

    class Config:
        env_file = ".env"

settings = Settings()
