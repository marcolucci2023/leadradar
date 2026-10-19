"""
Script de création des tables dans la base de données Neon.
À lancer UNE SEULE FOIS : python init_db.py
"""
import asyncio
import ssl

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.models import Base


async def create_tables():
    """Crée toutes les tables définies dans les modèles SQLAlchemy."""
    print("🔌 Connexion à la base de données...")
    print(f"   URL: {settings.DATABASE_URL[:50]}...")

    ssl_context = ssl.create_default_context()

    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        connect_args={"ssl": ssl_context},
    )

    async with engine.begin() as conn:
        print("📦 Création des tables...")
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("✅ Tables créées avec succès !")
    print("   - users")
    print("   - leads")


if __name__ == "__main__":
    asyncio.run(create_tables())