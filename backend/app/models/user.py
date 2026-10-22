import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy."""
    pass


class User(Base):
    """Un utilisateur de LeadRadar."""

    __tablename__ = "users"

    # Identifiant unique (UUID = un code aléatoire universel)
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Email unique (sert d'identifiant de connexion)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,  # Index = recherche rapide par email
    )

    # Mot de passe hashé (JAMAIS en clair !)
    hashed_password: Mapped[str] = mapped_column(String(255))

    # Nom complet
    full_name: Mapped[str] = mapped_column(String(255), default="")

    # Compte actif ?
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Date de création
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relation : un utilisateur peut avoir plusieurs leads
    leads: Mapped[list["Lead"]] = relationship(  # noqa: F821
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    # Relation : un utilisateur peut avoir plusieurs campagnes
    campaigns: Mapped[list["Campaign"]] = relationship(  # noqa: F821
        back_populates="owner",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"