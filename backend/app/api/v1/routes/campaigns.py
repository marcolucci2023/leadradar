from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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


class CampaignOut(BaseModel):
    id: str
    name: str
    description: str
    status: str
    lead_count: int = 0
    created_at: str


@router.post("/", response_model=CampaignOut)
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
):
    campaign = Campaign(
        name=data.name,
        description=data.description,
        owner_id=data.owner_id or "default",
    )
    db.add(campaign)
    await db.flush()

    for lead_id in data.lead_ids:
        cl = CampaignLead(campaign_id=campaign.id, lead_id=lead_id)
        db.add(cl)

    await db.commit()
    await db.refresh(campaign)

    return CampaignOut(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        lead_count=len(data.lead_ids),
        created_at=str(campaign.created_at),
    )


@router.get("/", response_model=list[CampaignOut])
async def list_campaigns(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).order_by(Campaign.created_at.desc())
    )
    campaigns = result.scalars().all()

    out = []
    for c in campaigns:
        count_result = await db.execute(
            select(CampaignLead).where(CampaignLead.campaign_id == c.id)
        )
        count = len(count_result.scalars().all())
        out.append(CampaignOut(
            id=c.id,
            name=c.name,
            description=c.description,
            status=c.status,
            lead_count=count,
            created_at=str(c.created_at),
        ))
    return out


@router.get("/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(404, "Campagne non trouvee")

    cl_result = await db.execute(
        select(CampaignLead).where(CampaignLead.campaign_id == campaign_id)
    )
    campaign_leads = cl_result.scalars().all()

    leads_data = []
    for cl in campaign_leads:
        lead_result = await db.execute(select(Lead).where(Lead.id == cl.lead_id))
        lead = lead_result.scalar_one_or_none()
        if lead:
            leads_data.append({
                "id": lead.id,
                "name": lead.name,
                "phone": lead.phone,
                "email": lead.email,
                "ai_score": lead.ai_score,
                "status": cl.status,
                "message": cl.message,
            })

    return {
        "id": campaign.id,
        "name": campaign.name,
        "description": campaign.description,
        "status": campaign.status,
        "leads": leads_data,
    }
