import ssl

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings

# Configuration SSL pour Neon (obligatoire en production)
# On crée un contexte SSL qui vérifie le certificat du serveur
ssl_context = ssl.create_default_context()

# Le moteur de connexion
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    connect_args={"ssl": ssl_context},  # ← C'est LA ligne qui remplace sslmode=require
)

# La fabrique de sessions
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """Fournit une session de base de données à chaque route FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()