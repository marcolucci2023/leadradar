from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel

from app.db.session import get_db
from app.models.campaign import Campaign, CampaignLead
from app.models.lead import Lead

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


class CampaignCreate(BaseModel):
    name: str
    description: str = ""
    lead_ids: list[str] = []
    owner_id: str = ""


class CampaignUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None


class AddLeadsRequest(BaseModel):
    lead_ids: list[str]


class CampaignOut(BaseModel):
    id: str
    name: str
    description: str
    status: str
    lead_count: int = 0
    skipped: int = 0
    created_at: str


async def _valid_lead_ids(db: AsyncSession, raw_ids: list[str]) -> list[str]:
    """Filtre les IDs vides, doublons et inexistants."""
    cleaned = list(dict.fromkeys((i or "").strip() for i in raw_ids))
    cleaned = [i for i in cleaned if i]
    if not cleaned:
        return []
    result = await db.execute(select(Lead.id).where(Lead.id.in_(cleaned)))
    existing = set(result.scalars().all())
    return [i for i in cleaned if i in existing]


@router.post("/", response_model=CampaignOut)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
):
    name = data.name.strip()
    if not name:
        raise HTTPException(400, "Le nom de la campagne est obligatoire")

    valid_ids = await _valid_lead_ids(db, data.lead_ids)
    skipped = len(data.lead_ids) - len(valid_ids)
    if skipped > 0:
        print(f"[CAMPAIGN] WARN {skipped} lead_id(s) ignore(s)")

    try:
        campaign = Campaign(name=name, description=data.description, owner_id=None)
        db.add(campaign)
        await db.flush()
        for lid in valid_ids:
            db.add(CampaignLead(campaign_id=campaign.id, lead_id=lid))
        await db.commit()
        await db.refresh(campaign)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(400, f"Erreur integrite: {e.orig}")

    print(f"[CAMPAIGN] OK '{campaign.name}' avec {len(valid_ids)} lead(s)")
    return CampaignOut(
        id=campaign.id, name=campaign.name, description=campaign.description,
        status=campaign.status, lead_count=len(valid_ids), skipped=skipped,
        created_at=str(campaign.created_at),
    )


@router.get("/", response_model=list[CampaignOut])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    campaigns = result.scalars().all()
    out = []
    for c in campaigns:
        r = await db.execute(
            select(func.count(CampaignLead.id)).where(CampaignLead.campaign_id == c.id)
        )
        out.append(CampaignOut(
            id=c.id, name=c.name, description=c.description,
            status=c.status, lead_count=r.scalar_one(),
            created_at=str(c.created_at),
        ))
    return out


@router.get("/{campaign_id}")
async def get_campaign(campaign_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, "Campagne non trouvee")

    cl_result = await db.execute(
        select(CampaignLead).where(CampaignLead.campaign_id == campaign_id)
    )
    campaign_leads = cl_result.scalars().all()

    leads_data = []
    for cl in campaign_leads:
        lr = await db.execute(select(Lead).where(Lead.id == cl.lead_id))
        lead = lr.scalar_one_or_none()
        if lead:
            leads_data.append({
                "id": lead.id,
                "name": lead.name,
                "address": lead.address,
                "phone": lead.phone,
                "email": lead.email,
                "website": lead.website,
                "ai_score": lead.ai_score if lead.ai_score and lead.ai_score > 0 else None,
                "status": cl.status,
                "message": cl.message,
            })

    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": campaign.description,
        "status": campaign.status,
        "leads": leads_data,
        "created_at": str(campaign.created_at),
    }


@router.put("/{campaign_id}")
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, "Campagne non trouvee")

    if data.name is not None:
        campaign.name = data.name.strip()
    if data.description is not None:
        campaign.description = data.description
    if data.status is not None and data.status in ("draft", "active", "paused", "completed"):
        campaign.status = data.status

    await db.commit()
    await db.refresh(campaign)
    print(f"[CAMPAIGN] OK '{campaign.name}' mis a jour (status={campaign.status})")
    return {"id": campaign.id, "name": campaign.name, "status": campaign.status}


@router.post("/{campaign_id}/leads")
async def add_leads_to_campaign(
    campaign_id: str,
    data: AddLeadsRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Campagne non trouvee")

    valid_ids = await _valid_lead_ids(db, data.lead_ids)

    # Ne pas ajouter les doublons
    existing = await db.execute(
        select(CampaignLead.lead_id).where(CampaignLead.campaign_id == campaign_id)
    )
    already = set(existing.scalars().all())
    new_ids = [i for i in valid_ids if i not in already]

    for lid in new_ids:
        db.add(CampaignLead(campaign_id=campaign_id, lead_id=lid))

    await db.commit()
    print(f"[CAMPAIGN] OK {len(new_ids)} lead(s) ajoute(s) a {campaign_id}")
    return {"added": len(new_ids), "skipped": len(data.lead_ids) - len(new_ids)}


@router.delete("/{campaign_id}/leads/{lead_id}")
async def remove_lead_from_campaign(
    campaign_id: str,
    lead_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CampaignLead).where(
            CampaignLead.campaign_id == campaign_id,
            CampaignLead.lead_id == lead_id,
        )
    )
    cl = result.scalar_one_or_none()
    if not cl:
        raise HTTPException(404, "Lead non trouve dans cette campagne")

    await db.delete(cl)
    await db.commit()
    print(f"[CAMPAIGN] OK lead {lead_id} retire de {campaign_id}")
    return {"removed": True}