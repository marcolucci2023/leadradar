"""
Service d'envoi d'emails via Resend (gratuit, 100/jour, 3000/mois).
"""
import httpx
from app.core.config import settings

RESEND_API_URL = "https://api.resend.com/emails"


async def send_email(
    to_email: str,
    subject: str,
    body: str,
    from_name: str = "LeadRadar",
) -> dict:
    """
    Envoie un email via Resend.
    Retourne {"success": True, "id": "..."} ou {"success": False, "error": "..."}.
    """
    api_key = settings.resend_api_key
    if not api_key:
        return {"success": False, "error": "Cle API Resend manquante dans .env"}

    from_email = f"{from_name} <onboarding@resend.dev>"

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(RESEND_API_URL, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            print(f"✅ Email envoye a {to_email}: {data.get('id', '')}")
            return {"success": True, "id": data.get("id", "")}
    except httpx.HTTPStatusError as e:
        err_msg = e.response.text[:200]
        print(f"❌ Erreur Resend {e.response.status_code}: {err_msg}")
        return {"success": False, "error": err_msg}
    except Exception as e:
        print(f"❌ Erreur envoi email: {e}")
        return {"success": False, "error": str(e)[:200]}
