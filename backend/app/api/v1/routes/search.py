from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.models.lead import Lead
from app.models.user import User
from app.services.search_service import search_businesses
from app.core.security import decode_token

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    city: str
    business_type: str
    radius: int = 5000


async def _get_user_id(request: Request, db: AsyncSession) -> str:
    """Recupere le user_id depuis le token JWT, sinon le premier user en base."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        try:
            payload = decode_token(token)
            sub = payload.get("sub", "")
            if sub:
                # Essayer par ID d'abord
                r = await db.execute(select(User).where(User.id == sub))
                user = r.scalar_one_or_none()
                if user:
                    return user.id
                # Essayer par email
                r = await db.execute(select(User).where(User.email == sub))
                user = r.scalar_one_or_none()
                if user:
                    return user.id
        except Exception as e:
            print(f"[SEARCH] WARN token decode failed: {e}")

    # Fallback : premier user en base
    r = await db.execute(select(User).limit(1))
    user = r.scalar_one_or_none()
    if user:
        return user.id
    return ""


@router.post("/")
async def search(
    req: SearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not req.city.strip():
        raise HTTPException(status_code=400, detail="Ville requise")
    if not req.business_type.strip():
        raise HTTPException(status_code=400, detail="Type de commerce requis")

    city = req.city.strip()
    btype = req.business_type.strip()

    # 1. Appel au moteur de recherche (Overpass / Nominatim / Telecontact)
    raw_data = await search_businesses(
        city=city,
        business_type=btype,
        radius=req.radius,
    )

    if isinstance(raw_data, list):
        raw_leads = raw_data
        source = "Overpass"
    else:
        raw_leads = raw_data.get("results", [])
        source = raw_data.get("source", "Overpass")

    if not raw_leads:
        return {"results": [], "total": 0, "source": source}

    # 2. Recuperer le user_id pour le FK owner_id
    user_id = await _get_user_id(request, db)
    if not user_id:
        print("[SEARCH] WARN aucun user en base, leads non sauvegardes")
        return {"results": raw_leads, "total": len(raw_leads), "source": source}

    # 3. Sauvegarder chaque lead en base (dedoublonnage par nom + type)
    saved = []
    created_count = 0
    updated_count = 0

    for raw in raw_leads:
        name = (raw.get("name") or raw.get("nom") or "").strip()
        if not name:
            continue

        address = (raw.get("address") or raw.get("addr") or raw.get("adresse") or "").strip()
        phone = (raw.get("phone") or raw.get("tel") or raw.get("telephone") or "").strip()
        website = (raw.get("website") or raw.get("site") or raw.get("url") or "").strip()
        lat = raw.get("latitude") or raw.get("lat") or 0.0
        lon = raw.get("longitude") or raw.get("lon") or 0.0
        lead_source = raw.get("source", source.lower())

        # Chercher un lead existant avec le meme nom + type
        existing = await db.execute(
            select(Lead).where(
                Lead.name == name,
                Lead.business_type == btype,
            ).limit(1)
        )
        lead = existing.scalar_one_or_none()

        if lead:
            # Mettre a jour les champs vides
            changed = False
            if address and not lead.address:
                lead.address = address
                changed = True
            if phone and not lead.phone:
                lead.phone = phone
                changed = True
            if website and not lead.website:
                lead.website = website
                changed = True
            if lat and lat != 0.0 and lead.latitude == 0.0:
                lead.latitude = float(lat)
                changed = True
            if lon and lon != 0.0 and lead.longitude == 0.0:
                lead.longitude = float(lon)
                changed = True
            if changed:
                updated_count += 1
        else:
            lead = Lead(
                name=name,
                address=address,
                phone=phone,
                website=website,
                latitude=float(lat),
                longitude=float(lon),
                business_type=btype,
                source=lead_source,
                owner_id=user_id,
            )
            db.add(lead)
            created_count += 1

        saved.append(lead)

    await db.commit()

    # 4. Refresh pour recuperer les IDs generes
    for lead in saved:
        await db.refresh(lead)

    print(f"[SEARCH] OK {created_count} crees, {updated_count} mis a jour, {len(saved)} total")

    # 5. Construire la reponse avec les vrais IDs
    output = []
    for lead in saved:
        output.append({
            "id": lead.id,
            "name": lead.name,
            "address": lead.address,
            "phone": lead.phone,
            "email": lead.email or "",
            "website": lead.website,
            "latitude": lead.latitude,
            "longitude": lead.longitude,
            "source": lead.source,
            "instagram": lead.instagram or "",
            "facebook": lead.facebook or "",
            "ai_score": lead.ai_score if lead.ai_score and lead.ai_score > 0 else None,
            "ai_reason": lead.ai_reason or "",
            "ai_message_subject": "",
            "ai_message_body": "",
        })

    return {"results": output, "total": len(output), "source": source}