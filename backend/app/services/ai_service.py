import os
import json
import re
import asyncio
from app.core.config import settings

_gemini_client = None


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
        _gemini_client = genai.Client()
    return _gemini_client


async def _call_gemini(prompt: str, max_retries: int = 3) -> str:
    c = _get_gemini()
    for attempt in range(max_retries):
        try:
            print(f"🤖 Gemini (essai {attempt + 1})...")
            resp = await asyncio.to_thread(
                c.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
            )
            print(f"✅ Gemini OK ({len(resp.text)} chars)")
            return resp.text
        except Exception as e:
            err = str(e)
            if ("429" in err or "503" in err) and attempt < max_retries - 1:
                wait = 65  # quota RPM Gemini se réinitialise chaque minute
                print(f"⏳ Rate limit, retry dans {wait}s...")
                await asyncio.sleep(wait)
            else:
                raise


def _extract_json(text: str) -> dict:
    text = text.strip()
    for attempt in [
        text,
        re.sub(r"```json\s*", "", re.sub(r"```\s*", "", text)).strip(),
    ]:
        try:
            return json.loads(attempt)
        except Exception:
            pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        for fix in [match.group(), match.group().replace("\n", " ")]:
            try:
                return json.loads(fix)
            except Exception:
                pass
    return {}


def _guess_activity(name: str, business_type: str) -> str:
    n = name.lower()
    rules = [
        (["factory", "café", "cafe", "pool", "brasserie", "bistro"], "restaurant et loisirs"),
        (["hôtel", "hotel", "riad", "resort", "palace"], "hôtellerie"),
        (["pharma", "santé", "medical", "clinique"], "santé"),
        (["beauty", "beauté", "spa", "coiffure"], "beauté et bien-être"),
        (["pizza", "pizzeria"], "pizzeria"),
        (["burger", "grill", "fast"], "restauration rapide"),
        (["requin", "poisson", "seafood"], "restaurant de fruits de mer"),
        (["tacos", "mexicain"], "restaurant mexicain"),
    ]
    for keywords, activity in rules:
        if any(w in n for w in keywords):
            return activity
    return business_type or "restaurant"


def _clean_city(city: str) -> str:
    c = city.strip()
    for suffix in [", Maroc", ", Morocco", ", maroc", ", France", ", france"]:
        c = c.replace(suffix, "")
    c = re.sub(r"[^\w\s.-]", "", c).strip()
    return c.title() if c else "Maroc"


# ============================================================
# SCORING (utilise les données enrichies)
# ============================================================
def calculate_score(lead: dict) -> tuple:
    score = 15
    reasons = ["Présence vérifiée (+15)"]

    w = lead.get("website", "")
    if w and not any(s in w for s in ["restopro", "tripadvisor", "mapcarta", "pagesjaunes", "linkedin.com/company/télécontact"]):
        score += 20
        reasons.append("Site web (+20)")
    elif w:
        score += 8
        reasons.append("Annuaire (+8)")
    else:
        reasons.append("Pas de site (0)")

    e = lead.get("email", "")
    if e and "@" in e:
        pts = 15 if "gmail" not in e else 10
        score += pts
        reasons.append(f"Email (+{pts})")
    else:
        reasons.append("Pas d'email (0)")

    p = lead.get("phone", "")
    if p and len(p) >= 8:
        score += 15
        reasons.append("Téléphone (+15)")
    else:
        reasons.append("Pas de tel (0)")

    a = lead.get("address", "")
    if len(a) > 10:
        score += 10
        reasons.append("Adresse (+10)")
    elif len(a) > 3:
        score += 5
        reasons.append("Adresse partielle (+5)")
    else:
        reasons.append("Adresse manquante (0)")

    ig = 1 if lead.get("instagram") else 0
    fb = 1 if lead.get("facebook") else 0
    s = ig + fb
    if s >= 2:
        score += 15
        reasons.append("IG+FB (+15)")
    elif s == 1:
        score += 8
        reasons.append("1 réseau (+8)")
    else:
        reasons.append("Pas de réseaux (0)")

    if lead.get("opening_hours"):
        score += 5
        reasons.append("Horaires (+5)")

    return min(score, 100), " | ".join(reasons)


# ============================================================
# FONCTIONS EXPORTÉES (compatibilité leads.py)
# ============================================================
async def score_lead(lead_name, lead_address, website="", business_type=""):
    score, reason = calculate_score({"name": lead_name, "address": lead_address, "website": website})
    return {"ai_score": score, "ai_reason": reason}


async def generate_prospection_message(lead_name, lead_address, website="", business_type=""):
    activity = _guess_activity(lead_name, business_type)
    prompt = f"""Copywriter B2B. Email court pour {lead_name} ({activity}) à {lead_address}. Site: {website or 'aucun'}.
Sujet max 60 chars, corps max 100 mots, bénéfice concret, ton chaleureux.
JSON: {{"subject": "sujet", "body": "corps"}}"""
    try:
        r = _extract_json(await _call_gemini(prompt))
        return {"ai_message_subject": r.get("subject", f"Idée pour {lead_name}"),
                "ai_message_body": r.get("body", f"Bonjour,\n\nNous aidons les {activity}s comme {lead_name}.\n\nCordialement")}
    except Exception:
        return {"ai_message_subject": f"Collaboration {lead_name}",
                "ai_message_body": f"Bonjour,\n\nNous aidons les {activity}s comme {lead_name}.\n\nCordialement"}


# ============================================================
# PIPELINE COMPLET
# ============================================================
async def score_and_message(lead_name, lead_address, website="", business_type="", extra_data=None, city=""):
    search_city = city
    if not search_city and lead_address:
        parts = [p.strip() for p in lead_address.split(",") if p.strip()]
        search_city = parts[0] if parts else "Maroc"
    search_city = _clean_city(search_city or "Maroc")

    # 1. ENRICHISSEMENT MULTI-SOURCES
    from app.services.web_search import enrich_lead_full
    facts = await enrich_lead_full(lead_name, search_city, website)

    # 2. Fusionner avec les données existantes
    extra = extra_data or {}

    def _pick(*vals):
        for v in vals:
            if v and str(v).strip():
                return str(v).strip()
        return ""

    lead = {
        "name": lead_name,
        "address": _pick(facts.get("address"), extra.get("address"), lead_address),
        "website": _pick(facts.get("website"), extra.get("website"), website),
        "phone": _pick(facts.get("phone"), extra.get("phone")),
        "email": _pick(facts.get("email"), extra.get("email")),
        "instagram": _pick(facts.get("instagram")),
        "facebook": _pick(facts.get("facebook")),
        "opening_hours": extra.get("opening_hours", ""),
        "description": extra.get("description", ""),
    }

    # 2b. Filtrer les faux sites web (LinkedIn, annuaires, etc.)
    BAD_SITE_PATTERNS = ["linkedin.com", "facebook.com", "instagram.com", "tripadvisor", "pagesjaunes", "telecontact", "eat.ma", "mapcarta"]
    if lead["website"] and any(p in lead["website"].lower() for p in BAD_SITE_PATTERNS):
        print(f"🚫 Faux site filtre: {lead['website']}")
        lead["website"] = ""

    # 3. Score (algorithmique + heuristique)
    score_algo, reason = calculate_score(lead)
    score_heuristic = facts.get("heuristic_score", 0)
    score = max(score_algo, score_heuristic)
    print(f"📊 {lead_name}: {score}/100 (algo={score_algo}, heuristique={score_heuristic})")

    # 4. Message Gemini
    activity = _guess_activity(lead_name, business_type)
    ctx = f"- Nom : {lead_name}\n- Activité : {activity}\n- Ville : {search_city}"
    if lead["website"]:
        ctx += f"\n- Site : {lead['website']}"
    else:
        ctx += "\n- Site : Aucun"
    if lead["phone"]:
        ctx += f"\n- Tel : {lead['phone']}"
    if lead["email"]:
        ctx += f"\n- Email : {lead['email']}"
    if lead["instagram"]:
        ctx += f"\n- Instagram : {lead['instagram']}"
    if lead["facebook"]:
        ctx += f"\n- Facebook : {lead['facebook']}"

    prompt = f"""Copywriter B2B expert, agence marketing digital.

Email COURT et PERSONNALISÉ :
{ctx}

RÈGLES :
1. Sujet max 60 caractères, accrocheur
2. Corps MAX 100 mots
3. Mentionne "{lead_name}" et {activity}
4. UN bénéfice chiffré
5. Si pas de site → propose création
6. Si réseaux sociaux → propose optimisation
7. Ton chaleureux, PAS robotique
8. PAS de "J'espère que ce message vous trouve bien"

JSON uniquement :
{{"subject": "sujet", "body": "corps"}}"""

    try:
        r = _extract_json(await _call_gemini(prompt))
        subject = r.get("subject", f"Idée pour {lead_name}")
        body = r.get("body", "")
        if not body:
            body = f"Bonjour,\n\nNous aidons les {activity}s comme {lead_name} à attirer +30% de clients.\n\nDisponible 15 min ?\n\nCordialement"
        print(f"✅ Message: {subject}")

    except Exception as e:
        err = str(e)
        if "429" in err:
            reason += " | ⚠️ Quota Gemini atteint"
        print(f"❌ Message erreur: {err[:100]}")

        # Message fallback INTELLIGENT
        subject = f"{lead_name} : +30% de clients à {search_city} ?"

        if not lead["website"] and not lead["instagram"]:
            body = (
                f"Bonjour l'équipe {lead_name},\n\n"
                f"Votre {activity} à {search_city} mérite d'être vu par plus de clients ! "
                f"Nous avons remarqué que vous n'avez pas encore de site web ni de présence "
                f"sur les réseaux sociaux.\n\n"
                f"Imaginez attirer 30% de clients locaux supplémentaires chaque mois grâce "
                f"à une présence digitale professionnelle.\n\n"
                f"Un échange de 15 minutes suffirait pour en discuter. "
                f"Quand seriez-vous disponible ?\n\n"
                f"Cordialement"
            )
        elif lead["website"] and not lead["instagram"]:
            body = (
                f"Bonjour l'équipe {lead_name},\n\n"
                f"J'ai visité votre site web et votre {activity} à {search_city} a un vrai potentiel ! "
                f"Cependant, sans présence sur Instagram ou Facebook, vous passez à côté "
                f"de nombreux clients locaux.\n\n"
                f"Nous aidons les établissements comme le vôtre à transformer leur visibilité "
                f"en réservations concrètes (+25% en moyenne).\n\n"
                f"Disponible 15 minutes cette semaine ?\n\n"
                f"Cordialement"
            )
        else:
            body = (
                f"Bonjour l'équipe {lead_name},\n\n"
                f"Votre {activity} à {search_city} a une belle présence en ligne ! "
                f"Nous pouvons vous aider à aller encore plus loin : optimisation SEO, "
                f"gestion des avis, publicités locales ciblées.\n\n"
                f"Nos clients voient en moyenne +30% de réservations en 3 mois.\n\n"
                f"Un bref échange de 15 minutes pour en discuter ?\n\n"
                f"Cordialement"
            )

    # 5. Retour avec les clés attendues par leads.py
    return {
        "ai_score": score,
        "ai_reason": reason,
        "ai_message_subject": subject,
        "ai_message_body": body,
        "enriched_phone": lead["phone"],
        "enriched_website": lead["website"],
        "enriched_email": lead["email"],
        "enriched_instagram": lead["instagram"],
        "enriched_facebook": lead["facebook"],
        "enriched_address": lead["address"],
    }
