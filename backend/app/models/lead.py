import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.user import Base


class Lead(Base):
    """Un lead (commerce local) dans LeadRadar."""

    __tablename__ = "leads"

    # Identifiant unique
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # === Informations de base (depuis Overpass/OpenStreetMap) ===
    name: Mapped[str] = mapped_column(String(500))
    address: Mapped[str] = mapped_column(String(1000), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    website: Mapped[str] = mapped_column(String(500), default="")
    latitude: Mapped[float] = mapped_column(Float, default=0.0)
    longitude: Mapped[float] = mapped_column(Float, default=0.0)
    business_type: Mapped[str] = mapped_column(
        String(100),
        index=True,  # Pour filtrer rapidement par type
    )
    source: Mapped[str] = mapped_column(
        String(50),
        default="overpass",  # overpass, manual, import
    )

    # === Enrichissement (ajouté après la recherche) ===
    email: Mapped[str] = mapped_column(String(255), default="")
    facebook: Mapped[str] = mapped_column(String(500), default="")
    instagram: Mapped[str] = mapped_column(String(500), default="")
    linkedin: Mapped[str] = mapped_column(String(500), default="")

    # === IA (scoring + message) ===
    ai_score: Mapped[int] = mapped_column(Integer, default=0)
    ai_reason: Mapped[str] = mapped_column(Text, default="")
    ai_message: Mapped[str] = mapped_column(Text, default="")

    # === Pipeline de vente ===
    stage: Mapped[str] = mapped_column(
        String(50),
        default="new",  # new, contacted, interested, converted, lost
    )

    # === Relations ===
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        index=True,
    )
    owner: Mapped["User"] = relationship(back_populates="leads")  # noqa: F821

    # === Métadonnées ===
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Lead {self.name} ({self.business_type})>"