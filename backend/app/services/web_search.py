"""
Recherche web multi-sources gratuite pour l'enrichissement de leads.
Sources : DuckDuckGo HTML, Google Maps HTML, Telecontact.ma
"""
import asyncio
import re
import unicodedata
from urllib.parse import quote_plus, unquote, parse_qs, urlparse
from collections import Counter

import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

BLOCKED_DOMAINS = (
    "tripadvisor", "yelp", "pagesjaunes", "yellowpages", "foursquare",
    "zomato", "thefork", "restopro", "google.com", "youtube.com",
    "tiktok.com", "linkedin.com", "pinterest", "wikipedia",
    "mapcarta", "zoologiste", "nicelocal", "worldorgs", "sluglines",
    "telecontact.ma", "eat.ma", "mappy", "bing.com", "restaurantguru", "petitfute", "booking.com", "hotels.com",
)

EMAIL_REGEX = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
BAD_EMAIL_PATTERNS = ("noreply", "no-reply", "example.com", "test.com", "sentry", "webpack", "sentry-nextjs")


def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()


def _is_blocked(url: str) -> bool:
    url_norm = _normalize(url)
    return any(d in url_norm for d in BLOCKED_DOMAINS)


def _clean_address(addr: str) -> str:
    addr = addr.replace("\\", "").replace("\n", " ").replace("\r", "")
    addr = re.sub(r"\s+", " ", addr).strip()
    return addr


def _is_good_email(email: str) -> bool:
    """Accepte gmail/yahoo (utilises par les pros au Maroc), rejette juste le spam."""
    e = email.lower().strip()
    if not EMAIL_REGEX.match(e):
        return False
    for bad in BAD_EMAIL_PATTERNS:
        if bad in e:
            return False
    return True


def _extract_emails_from_text(text: str) -> list:
    """Extrait tous les emails valides d'un texte brut."""
    found = EMAIL_REGEX.findall(text)
    return list(set(e.lower() for e in found if _is_good_email(e)))


# ============================================================
# 1. DUCKDUCKGO HTML
# ============================================================
async def duckduckgo_search(query: str, max_results: int = 10) -> list:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}&kl=fr-fr"
    try:
        async with httpx.AsyncClient(
            timeout=10.0, follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"},
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
    except Exception as e:
        print(f"⚠️ DDG search failed: {e}")
        return []

    soup = BeautifulSoup(r.text, "lxml")
    results = []
    for a in soup.select("a.result__a")[:max_results]:
        href = a.get("href", "")
        if "uddg=" in href:
            qs = parse_qs(urlparse(href).query)
            href = unquote(qs.get("uddg", [""])[0])
        if href.startswith("http"):
            results.append({"url": href, "title": a.get_text(strip=True)})

    # Aussi extraire les snippets pour les emails
    for snippet in soup.select(".result__snippet"):
        text = snippet.get_text(strip=True)
        emails = _extract_emails_from_text(text)
        if emails:
            results.append({"url": "", "title": text, "email": emails[0]})

    return results


# ============================================================
# 2. SITE OFFICIEL + RESEAUX SOCIAUX + EMAIL via DDG
# ============================================================
async def find_official_site_and_socials(name: str, city: str) -> dict:
    out = {"website": "", "facebook": "", "instagram": "", "email": ""}
    safe_name = name.replace('"', "")

    # Site officiel
    try:
        results = await duckduckgo_search(f"{safe_name} {city}")
        for r in results:
            url = r.get("url", "")
            if not url:
                continue
            if _is_blocked(url):
                continue
            if "facebook.com" in url or "instagram.com" in url:
                continue
            out["website"] = url
            print(f"✅ DDG site officiel: {url}")
            break
        # Chercher email dans les snippets
        for r in results:
            if r.get("email"):
                out["email"] = r["email"]
                print(f"✅ DDG email (snippet): {out['email']}")
                break
    except Exception as e:
        print(f"⚠️ DDG site search error: {e}")

    await asyncio.sleep(1)

    # Facebook
    try:
        results = await duckduckgo_search(f'site:facebook.com "{safe_name}" {city}')
        for r in results:
            url = r.get("url", "")
            if "facebook.com" in url and "/sharer" not in url and "/dialog" not in url:
                out["facebook"] = url.split("?")[0]
                print(f"✅ DDG Facebook: {out['facebook']}")
                break
    except Exception as e:
        print(f"⚠️ DDG Facebook error: {e}")

    await asyncio.sleep(1)

    # Instagram
    try:
        results = await duckduckgo_search(f'site:instagram.com "{safe_name}" {city}')
        for r in results:
            url = r.get("url", "")
            if "instagram.com" in url and "/p/" not in url and "/reel/" not in url:
                out["instagram"] = url.split("?")[0]
                print(f"✅ DDG Instagram: {out['instagram']}")
                break
    except Exception as e:
        print(f"⚠️ DDG Instagram error: {e}")

    await asyncio.sleep(1)

    # EMAIL via DDG recherche ciblee
    if not out["email"]:
        try:
            results = await duckduckgo_search(f'"{safe_name}" email contact {city}')
            for r in results:
                title = r.get("title", "")
                emails = _extract_emails_from_text(title)
                if emails:
                    out["email"] = emails[0]
                    print(f"✅ DDG email (search): {out['email']}")
                    break
        except Exception as e:
            print(f"⚠️ DDG email error: {e}")

    return out


# ============================================================
# 3. GOOGLE MAPS HTML (tel + adresse + email + facebook)
# ============================================================
def _scrape_gmaps_sync(name: str, city: str) -> dict:
    """Version synchrone de Playwright (tourne dans un thread)."""
    from playwright.sync_api import sync_playwright
    from urllib.parse import quote_plus
    import re as _re

    out = {"phone": "", "address": "", "website": "", "email": "", "facebook": ""}
    query = quote_plus(f"{name} {city}")
    url = f"https://www.google.com/maps/search/{query}?hl=fr"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            context = browser.new_context(
                user_agent=UA,
                locale="fr-FR",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(5000)

            content = page.content()

            # Telephone
            try:
                phone_el = page.query_selector('button[data-item-id^="phone:"]')
                if phone_el:
                    txt = phone_el.inner_text()
                    out["phone"] = _re.sub(r"[^\d+]", "", txt)
                    print(f"  ✅ GMaps telephone: {out['phone']}")
            except Exception:
                pass

            # Adresse
            try:
                addr_el = page.query_selector('button[data-item-id="address"]')
                if addr_el:
                    out["address"] = _clean_address(addr_el.inner_text())
                    print(f"  ✅ GMaps adresse: {out['address']}")
            except Exception:
                pass

            # Site web
            try:
                site_el = page.query_selector('a[data-item-id="authority"]')
                if site_el:
                    href = site_el.get_attribute("href")
                    if href and not _is_blocked(href):
                        out["website"] = href
                        print(f"  ✅ GMaps site: {out['website']}")
            except Exception:
                pass

            # Email
            emails = _extract_emails_from_text(content)
            if emails:
                out["email"] = emails[0]
                print(f"  ✅ GMaps email: {out['email']}")

            # Facebook
            try:
                fb_el = page.query_selector('a[href*="facebook.com"]')
                if fb_el:
                    href = fb_el.get_attribute("href")
                    if href and "/sharer" not in href and "/dialog" not in href:
                        out["facebook"] = href.split("?")[0]
                        print(f"  ✅ GMaps Facebook: {out['facebook']}")
            except Exception:
                pass

            browser.close()

    except Exception as e:
        print(f"  ⚠️ Playwright GMaps error: {e}")

    return out


async def scrape_google_maps(name: str, city: str) -> dict:
    """Wrapper async qui lance Playwright sync dans un thread."""
    try:
        result = await asyncio.to_thread(_scrape_gmaps_sync, name, city)
        return result
    except Exception as e:
        print(f"⚠️ GMaps thread failed: {e}")
        return {"phone": "", "address": "", "website": "", "email": "", "facebook": ""}




# ============================================================
# 4. TELECONTACT.MA
# ============================================================
async def scrape_telecontact(name: str, city: str) -> dict:
    out = {"phone": "", "address": "", "website": "", "email": ""}
    city_clean = city.split(",")[0].strip()
    url = f"https://www.telecontact.ma/{quote_plus(name.lower())}/{quote_plus(city_clean.lower().replace(' ', '-'))}"

    try:
        async with httpx.AsyncClient(
            timeout=10.0, follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"},
        ) as client:
            r = await client.get(url)
            soup = BeautifulSoup(r.text, "lxml")
            html = r.text
    except Exception as e:
        print(f"⚠️ Telecontact failed: {e}")
        return out

    # Telephone
    tel_el = soup.select_one("[itemprop='telephone'], .tel, .phone, a[href^='tel:']")
    if tel_el:
        tel_text = tel_el.get_text(strip=True) or tel_el.get("href", "").replace("tel:", "")
        if tel_text and len(tel_text) >= 8:
            out["phone"] = re.sub(r"[\s\-]", "", tel_text)
            print(f"✅ Telecontact tel: {out['phone']}")

    # Adresse
    addr_el = soup.select_one("[itemprop='address'], .address, .adr")
    if addr_el:
        out["address"] = _clean_address(addr_el.get_text(" ", strip=True))
        print(f"✅ Telecontact adresse: {out['address']}")

    # Site web (filtrer les liens Telecontact eux-memes)
    for link in soup.select("a[href^='http'][target='_blank']"):
        site_url = link.get("href", "")
        if _is_blocked(site_url):
            continue
        if "facebook.com" in site_url or "instagram.com" in site_url:
            continue
        out["website"] = site_url
        print(f"✅ Telecontact site: {out['website']}")
        break

    # Email : chercher dans les liens mailto: d'abord
    for a in soup.select("a[href^='mailto:']"):
        email = a["href"].replace("mailto:", "").split("?")[0].strip()
        if _is_good_email(email) and "telecontact" not in email:
            out["email"] = email
            print(f"✅ Telecontact email (mailto): {out['email']}")
            break

    # Sinon chercher dans le HTML brut (mais exclure telecontact.ma)
    if not out["email"]:
        emails = _extract_emails_from_text(html)
        for e in emails:
            if "telecontact" not in e:
                out["email"] = e
                print(f"✅ Telecontact email (html): {out['email']}")
                break

    return out


# ============================================================
# 5. SCRAPING PAGE CONTACT DU SITE WEB
# ============================================================
async def scrape_website_for_email(website: str) -> str:
    if not website or _is_blocked(website):
        return ""

    base = website.rstrip("/")
    pages_to_try = [base, f"{base}/contact", f"{base}/contactez-nous", f"{base}/about", f"{base}/a-propos"]

    try:
        async with httpx.AsyncClient(
            timeout=8.0, follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"},
        ) as client:
            for page_url in pages_to_try:
                try:
                    r = await client.get(page_url)
                    if r.status_code == 200:
                        soup = BeautifulSoup(r.text, "lxml")
                        for a in soup.select("a[href^='mailto:']"):
                            email = a["href"].replace("mailto:", "").split("?")[0].strip()
                            if _is_good_email(email):
                                print(f"✅ Email site (mailto): {email}")
                                return email
                        emails = _extract_emails_from_text(r.text)
                        if emails:
                            print(f"✅ Email site (html): {emails[0]}")
                            return emails[0]
                except Exception:
                    continue
    except Exception as e:
        print(f"⚠️ Scraping site email error: {e}")

    return ""


# ============================================================
# 6. FUSION MULTI-SOURCES
# ============================================================

# ============================================================
# 4b. TELECONTACT.MA - RECHERCHE LISTE (pour search initial)
# ============================================================
async def search_telecontact_list(business_type: str, city: str) -> list:
    """Scrape Telecontact avec pagination (3 pages)."""
    city_clean = city.split(',')[0].strip()
    query = f"{business_type} {city_clean}"
    urls_to_try = [
        f"https://www.telecontact.ma/{quote_plus(business_type.lower().replace(' ', '-'))}/{quote_plus(city_clean.lower().replace(' ', '-'))}",
        f"https://www.telecontact.ma/{quote_plus(query.replace(chr(32), chr(45)).lower())}",
    ]

    base_url = ""
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}) as client:
        for url in urls_to_try:
            try:
                r = await client.get(url)
                if r.status_code == 200 and len(r.text) > 2000:
                    base_url = str(r.url)
                    print(f"OK Telecontact OK: {base_url}")
                    break
                else:
                    print(f"WARN Telecontact {r.status_code}: {url}")
            except Exception as e:
                print(f"WARN Telecontact try failed: {e}")
                continue

    if not base_url:
        print("WARN Telecontact HTTP 404 pour toutes les URLs")
        return []

    results = []
    print(f"[TEL] Telecontact recherche: {query}")

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"}) as client:
        for page in range(1, 4):
            if page == 1:
                page_url = base_url
            else:
                page_url = f"{base_url}&page={page}"
            try:
                r = await client.get(page_url)
                if r.status_code != 200 or len(r.text) < 2000:
                    print(f"WARN Telecontact page {page}: {r.status_code}")
                    break
            except Exception as e:
                print(f"WARN Telecontact page {page} failed: {e}")
                break

            soup = BeautifulSoup(r.text, "lxml")
            items = soup.select('.result-search-item-non-annonceur')
            if not items:
                print(f"WARN Telecontact page {page}: 0 items, arret")
                break

            for item in items:
                name = item.get('data-rs-comp', '')
                if not name:
                    name_el = item.select_one('h2[itemprop="name"] a, h2 a')
                    name = name_el.get_text(strip=True) if name_el else ''
                if not name or len(name) < 3:
                    continue

                phone = ''
                tel_el = item.select_one('[itemprop="telephone"], a[href^="tel:"]')
                if tel_el:
                    phone = re.sub(r'[\s\-]', '', tel_el.get_text(strip=True) or tel_el.get('href', '').replace('tel:', ''))

                address = ''
                addr_el = item.select_one('[itemprop="streetAddress"]')
                if addr_el:
                    address = _clean_address(addr_el.get_text(' ', strip=True))

                website = ''
                for link in item.select('a[href^="http"]'):
                    href = link.get('href', '')
                    if not _is_blocked(href) and 'facebook' not in href and 'instagram' not in href and 'telecontact' not in href:
                        website = href
                        break

                email = ''
                for a in item.select('a[href^="mailto:"]'):
                    e = a['href'].replace('mailto:', '').split('?')[0].strip()
                    if _is_good_email(e) and 'telecontact' not in e:
                        email = e
                        break

                results.append({
                    'name': name,
                    'address': address or city_clean,
                    'phone': phone,
                    'website': website,
                    'email': email,
                    'lat': None,
                    'lon': None,
                    'business_type': business_type,
                    'opening_hours': '',
                    'description': '',
                    'google_maps': '',
                })

            print(f"OK Telecontact page {page}: {len(items)} items")

    print(f'OK Telecontact: {len(results)} resultats')
    return results


    for item in items[:50]:
        # Nom
        name_el = item.select_one("h2, h3, .name, .title, a[href]")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        if not name or len(name) < 3:
            continue

        # Telephone
        phone = ""
        tel_el = item.select_one("[itemprop='telephone'], .tel, .phone, a[href^='tel:']")
        if tel_el:
            phone = re.sub(r"[\s\-]", "", tel_el.get_text(strip=True) or tel_el.get('href', '').replace('tel:', ''))

        # Adresse
        address = ""
        addr_el = item.select_one("[itemprop='address'], .address, .adr, .location")
        if addr_el:
            address = _clean_address(addr_el.get_text(' ', strip=True))

        # Site web
        website = ""
        for link in item.select("a[href^='http']"):
            href = link.get('href', '')
            if not _is_blocked(href) and 'facebook' not in href and 'instagram' not in href and 'telecontact' not in href:
                website = href
                break

        # Email
        email = ""
        for a in item.select("a[href^='mailto:']"):
            e = a['href'].replace('mailto:', '').split('?')[0].strip()
            if _is_good_email(e) and 'telecontact' not in e:
                email = e
                break

        results.append({
            "name": name,
            "address": address or city_clean,
            "phone": phone,
            "website": website,
            "email": email,
            "lat": None,
            "lon": None,
            "business_type": business_type,
            "opening_hours": "",
            "description": "",
            "google_maps": "",
        })

    print(f"✅ Telecontact: {len(results)} resultats")
    return results


def merge_sources(sources: dict) -> dict:
    fields = ["phone", "email", "website", "facebook", "instagram", "address"]
    merged = {f: "" for f in fields}
    confidence = {f: 0 for f in fields}

    for field in fields:
        values = []
        for src_name, data in sources.items():
            v = (data or {}).get(field, "").strip()
            if v:
                if field == "website" and _is_blocked(v):
                    continue
                if field == "email" and not _is_good_email(v):
                    continue
                if field == "email" and "telecontact" in v:
                    continue
                values.append(v)

        if values:
            most_common, count = Counter(values).most_common(1)[0]
            merged[field] = most_common
            confidence[field] = count

    score = 15
    if merged["phone"] and len(merged["phone"]) >= 8:
        score += 20
    if merged["address"] and len(merged["address"]) > 5:
        score += 15
    if merged["website"]:
        score += 15
    if merged["email"]:
        score += 15
    if merged["facebook"] or merged["instagram"]:
        score += 10

    for f in ("phone", "address"):
        if confidence[f] >= 2:
            score += 5

    merged["heuristic_score"] = min(score, 95)
    return merged


# ============================================================
# PIPELINE PRINCIPAL
# ============================================================
async def enrich_lead_full(name: str, city: str, website: str = "") -> dict:
    print(f"\n🔍 Pipeline enrichissement: '{name}' a {city}")
    sources = {}

    # ETAPE 1 : DDG (site + reseaux + email)
    try:
        ws = await find_official_site_and_socials(name, city)
        sources["ddg"] = ws
        if not website and ws.get("website"):
            website = ws["website"]
    except Exception as e:
        print(f"⚠️ Etape DDG echouee: {e}")

    # ETAPE 2 : Google Maps (tel + adresse + email + facebook)
    try:
        gm = await scrape_google_maps(name, city)
        sources["gmaps"] = gm
    except Exception as e:
        print(f"⚠️ Etape GMaps echouee: {e}")

    await asyncio.sleep(1)

    # ETAPE 3 : Telecontact
    try:
        tc = await scrape_telecontact(name, city)
        sources["telecontact"] = tc
    except Exception as e:
        print(f"⚠️ Etape Telecontact echouee: {e}")

    # ETAPE 4 : Scraping site web pour email
    if website and not _is_blocked(website):
        try:
            email_from_site = await scrape_website_for_email(website)
            if email_from_site:
                sources["website_email"] = {"email": email_from_site}

            from app.services.enrichment import enrich_lead_from_website
            web = await enrich_lead_from_website(website)
            sources["website"] = {
                "phone": web.get("phone", ""),
                "email": web.get("email", ""),
                "facebook": web.get("social", {}).get("facebook", ""),
                "instagram": web.get("social", {}).get("instagram", ""),
                "website": website,
            }
        except Exception as e:
            print(f"⚠️ Etape scraping site echouee: {e}")

    # Fusion
    result = merge_sources(sources)
    print(f"📊 Fusion: score heuristique {result['heuristic_score']}/100")
    for k, v in result.items():
        if v and k != "heuristic_score":
            print(f"   {k}: {v}")

    return result
