from pydantic import BaseModel


class SearchRequest(BaseModel):
    """Ce que l'utilisateur envoie pour faire une recherche."""
    city: str
    business_type: str
    radius_km: int = 5


class LeadResult(BaseModel):
    """Un lead trouve via Overpass/OpenStreetMap (version enrichie)."""
    name: str
    address: str = ""
    phone: str = ""
    website: str = ""
    email: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    business_type: str = ""
    source: str = "overpass"
    opening_hours: str = ""
    description: str = ""
    google_maps: str = ""


class SearchResponse(BaseModel):
    """La reponse complete d'une recherche."""
    city: str
    business_type: str
    total_found: int
    leads: list[LeadResult]