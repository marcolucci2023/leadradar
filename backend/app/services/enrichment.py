import re
import logging

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Domaines d'annuaires connus (pas de vrais sites de restaurants)
DIRECTORY_DOMAINS = [
    "restopro.ma", "tripadvisor.", "yelp.", "pagesjaunes.",
    "yellowpages.", "foursquare.", "zomato.", "thefork.",
    "google.com/maps", "facebook.com/pg/", "instagram.com/",
]


def _is_directory_url(url: str) -> bool:
    """Vérifie si une URL est un annuaire plutôt qu'un vrai site web."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in DIRECTORY_DOMAINS)


async def _fetch_page(url: str) -> str | None:
    """Télécharge une page web. Renvoie le HTML ou None si erreur."""
    try:
        async with httpx.AsyncClient(
            timeout=8.0,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8,ar;q=0.7",
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:
        logger.debug(f"⚠️ Impossible de charger {url} : {type(e).__name__}")
        return None


def _extract_emails(html: str) -> list[str]:
    """Extrait les emails du HTML en filtrant les faux positifs."""
    pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    emails = pattern.findall(html)

    valid = []
    for email in emails:
        email_lower = email.lower()
        # Exclure les faux positifs
        if any(ext in email_lower for ext in [".png", ".jpg", ".gif", ".svg", ".css", ".js", ".woff", ".webp"]):
            continue
        if any(domain in email_lower for domain in ["sentry.io", "example.com", "wixpress", "squarespace", "webpack"]):
            continue
        if email_lower not in valid:
            valid.append(email_lower)

    return valid


def _extract_phones(html: str) -> list[str]:
    """Extrait les numéros de téléphone du HTML."""
    # Patterns pour différents formats de téléphone
    patterns = [
        # Format marocain : 05 22 XX XX XX, +212 5XX XXX XXX
        r"(?:\+212|0)[\s.-]?[5-7][\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}",
        # Format français : 01 XX XX XX XX, +33 1 XX XX XX XX
        r"(?:\+33|0)[\s.-]?[1-9][\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}[\s.-]?\d{2}",
        # Format international générique : +XXX XXX XXX XXXX
        r"\+\d{1,3}[\s.-]?\d{3,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}",
    ]

    phones = []
    for pattern in patterns:
        found = re.findall(pattern, html)
        for phone in found:
            # Nettoyer : garder seulement chiffres, +, espaces
            clean = re.sub(r"[^\d+\s]", "", phone).strip()
            if len(clean) >= 8 and clean not in phones:
                phones.append(clean)

    return phones


def _extract_social_links(soup: BeautifulSoup) -> dict:
    """Extrait les liens de réseaux sociaux depuis les balises <a>."""
    result = {"facebook": "", "instagram": "", "linkedin": ""}

    social_patterns = {
        "facebook": ["facebook.com/", "fb.com/", "fb.me/"],
        "instagram": ["instagram.com/", "instagr.am/"],
        "linkedin": ["linkedin.com/"],
    }

    for link in soup.find_all("a", href=True):
        href = link["href"].lower()

        for platform, domains in social_patterns.items():
            if not result[platform] and any(d in href for d in domains):
                clean_url = link["href"].split("?")[0].split("#")[0]
                # Exclure les liens de partage (facebook.com/sharer, etc.)
                if "sharer" not in clean_url and "share" not in clean_url:
                    result[platform] = clean_url

    return result


async def enrich_lead_from_website(website: str) -> dict:
    """
    Enrichissement amélioré :
    - Visite la page d'accueil + /contact + /about
    - Extrait emails, téléphones, réseaux sociaux
    - Détecte si le site est un annuaire ou un vrai site
    """
    result = {
        "email": "",
        "phone_from_web": "",
        "facebook": "",
        "instagram": "",
        "linkedin": "",
        "is_directory": False,
        "real_website": "",
    }

    if not website or not website.startswith("http"):
        return result

    # Vérifier si c'est un annuaire
    if _is_directory_url(website):
        result["is_directory"] = True
        logger.info(f"📋 {website} est un annuaire, enrichissement limité")
        # On ne visite pas les annuaires, ça ne sert à rien
        return result

    # Pages à visiter
    base_url = website.rstrip("/")
    urls_to_try = [
        base_url,
        f"{base_url}/contact",
        f"{base_url}/contactez-nous",
        f"{base_url}/about",
        f"{base_url}/a-propos",
    ]

    all_emails = []
    all_phones = []
    social = {"facebook": "", "instagram": "", "linkedin": ""}

    for url in urls_to_try:
        html = await _fetch_page(url)
        if not html:
            continue

        # Extraire les emails
        emails = _extract_emails(html)
        all_emails.extend(emails)

        # Extraire les téléphones
        phones = _extract_phones(html)
        all_phones.extend(phones)

        # Extraire les réseaux sociaux (seulement depuis la page d'accueil)
        if url == base_url:
            soup = BeautifulSoup(html, "lxml")
            social = _extract_social_links(soup)

            # Chercher le vrai site web dans les liens (si on est sur un annuaire)
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if (
                    href.startswith("http")
                    and not _is_directory_url(href)
                    and "google" not in href.lower()
                    and "maps" not in href.lower()
                ):
                    result["real_website"] = href
                    break

        # Si on a trouvé un email, pas besoin de continuer
        if all_emails:
            break

    # Remplir les résultats
    if all_emails:
        result["email"] = list(dict.fromkeys(all_emails))[0]
    if all_phones:
        result["phone_from_web"] = list(dict.fromkeys(all_phones))[0]
    result.update(social)

    logger.info(
        f"🔎 Enrichissement {website} : "
        f"email={'✅' if result['email'] else '❌'} | "
        f"tel={'✅' if result['phone_from_web'] else '❌'} | "
        f"fb={'✅' if result['facebook'] else '❌'} | "
        f"ig={'✅' if result['instagram'] else '❌'}"
    )

    return result