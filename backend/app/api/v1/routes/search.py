from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.services.search_service import search_businesses

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    city: str
    business_type: str
    radius: int = 5000


@router.post("/")
async def search(req: SearchRequest):
    if not req.city.strip():
        raise HTTPException(status_code=400, detail="Ville requise")
    if not req.business_type.strip():
        raise HTTPException(status_code=400, detail="Type de commerce requis")

    results = await search_businesses(
        city=req.city.strip(),
        business_type=req.business_type.strip(),
        radius=req.radius,
    )
    return results