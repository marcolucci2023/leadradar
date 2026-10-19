from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.services.ai_service import score_lead, generate_prospection_message, score_and_message
from app.services.email_service import send_email

router = APIRouter(prefix="/leads", tags=["leads"])


class EnrichRequest(BaseModel):
    website: str


class ScoreRequest(BaseModel):
    name: str
    address: str
    website: str = ""
    business_type: str = ""


class FullPipelineRequest(BaseModel):
    name: str
    address: str
    website: str = ""
    business_type: str = ""
    phone: str = ""
    email: str = ""
    opening_hours: str = ""
    description: str = ""
    city: str = ""


@router.post("/enrich")
async def enrich_lead(req: EnrichRequest):
    if not req.website:
        raise HTTPException(status_code=400, detail="Website requis")
    from app.services.enrichment import enrich_lead_from_website
    result = await enrich_lead_from_website(req.website)
    return result


@router.post("/score")
async def score(req: ScoreRequest):
    return await score_lead(req.name, req.address, req.website, req.business_type)


@router.post("/generate-message")
async def gen_message(req: ScoreRequest):
    return await generate_prospection_message(req.name, req.address, req.website, req.business_type)


@router.post("/full-pipeline")
async def full_pipeline(req: FullPipelineRequest, language: str = Query("fr")):
    extra_data = {
        "phone": req.phone,
        "email": req.email,
        "opening_hours": req.opening_hours,
        "description": req.description,
        "address": req.address,
        "website": req.website,
    }

    try:
        ai_result = await score_and_message(
            lead_name=req.name,
            lead_address=req.address,
            website=req.website,
            business_type=req.business_type,
            extra_data=extra_data,
            city=req.city,
        )
    except Exception as e:
        print(f"⚠️ Pipeline error: {e}")
        ai_result = {
            "ai_score": 15,
            "ai_reason": f"Erreur: {str(e)[:100]}",
            "ai_message_subject": "",
            "ai_message_body": "",
            "enriched_phone": "",
            "enriched_website": "",
            "enriched_email": "",
            "enriched_instagram": "",
            "enriched_facebook": "",
            "enriched_address": "",
        }

    return {
        "name": req.name,
        "address": ai_result.get("enriched_address") or req.address,
        "website": ai_result.get("enriched_website") or req.website,
        "email": ai_result.get("enriched_email") or req.email,
        "phone": ai_result.get("enriched_phone") or req.phone,
        "instagram": ai_result.get("enriched_instagram", ""),
        "facebook": ai_result.get("enriched_facebook", ""),
        "ai_score": ai_result.get("ai_score", 15),
        "ai_reason": ai_result.get("ai_reason", ""),
        "ai_message_subject": ai_result.get("ai_message_subject", ""),
        "ai_message_body": ai_result.get("ai_message_body", ""),
    }

class SendEmailRequest(BaseModel):
    to_email: str
    subject: str
    body: str


@router.post("/send-email")
async def send_lead_email(req: SendEmailRequest):
    if not req.to_email or "@" not in req.to_email:
        raise HTTPException(status_code=400, detail="Email invalide")
    result = await send_email(
        to_email=req.to_email,
        subject=req.subject,
        body=req.body,
    )
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return {"status": "sent", "id": result.get("id", "")}
