import httpx
import re
import time

# ============================================================
# DICTIONNAIRE VILLES MENA + AFRIQUE (fallback geocoding)
# ============================================================
MENA_CITIES = {
    "casablanca": (33.5731, -7.5898, "Casablanca, Maroc"),
    "rabat": (34.0209, -6.8416, "Rabat, Maroc"),
    "marrakech": (31.6295, -7.9811, "Marrakech, Maroc"),
    "fes": (34.0181, -5.0078, "Fès, Maroc"),
    "fès": (34.0181, -5.0078, "Fès, Maroc"),
    "tanger": (35.7595, -5.8340, "Tanger, Maroc"),
    "agadir": (30.4278, -9.5981, "Agadir, Maroc"),
    "meknes": (33.8935, -5.5473, "Meknès, Maroc"),
    "oujda": (34.6814, -1.9086, "Oujda, Maroc"),
    "kenitra": (34.2610, -6.5802, "Kénitra, Maroc"),
    "tetouan": (35.5785, -5.3684, "Tétouan, Maroc"),
    "nador": (35.1681, -2.9333, "Nador, Maroc"),
    "el jadida": (33.2316, -8.5007, "El Jadida, Maroc"),
    "eljadida": (33.2316, -8.5007, "El Jadida, Maroc"),
    "mohammedia": (33.6866, -7.3830, "Mohammedia, Maroc"),
    "dakhla": (23.6848, -15.9579, "Dakhla, Maroc"),
    "laayoune": (27.1536, -13.2033, "Laâyoune, Maroc"),
    "tunis": (36.8065, 10.1815, "Tunis, Tunisie"),
    "sfax": (34.7406, 10.7603, "Sfax, Tunisie"),
    "sousse": (35.8256, 10.6369, "Sousse, Tunisie"),
    "alger": (36.7538, 3.0588, "Alger, Algérie"),
    "oran": (35.6971, -0.6309, "Oran, Algérie"),
    "constantine": (36.3650, 6.6147, "Constantine, Algérie"),
    "le caire": (30.0444, 31.2357, "Le Caire, Égypte"),
    "cairo": (30.0444, 31.2357, "Le Caire, Égypte"),
    "alexandrie": (31.2001, 29.9187, "Alexandrie, Égypte"),
    "dubai": (25.2048, 55.2708, "Dubaï, EAU"),
    "dubaï": (25.2048, 55.2708, "Dubaï, EAU"),
    "abu dhabi": (24.4539, 54.3773, "Abu Dhabi, EAU"),
    "riyadh": (24.7136, 46.6753, "Riyad, Arabie Saoudite"),
    "jeddah": (21.4858, 39.1925, "Djeddah, Arabie Saoudite"),
    "doha": (25.2854, 51.5310, "Doha, Qatar"),
    "kuwait": (29.3759, 47.9774, "Koweït City, Koweït"),
    "amman": (31.9454, 35.9284, "Amman, Jordanie"),
    "beirut": (33.8938, 35.5018, "Beyrouth, Liban"),
    "beyrouth": (33.8938, 35.5018, "Beyrouth, Liban"),
    "baghdad": (33.3152, 44.3661, "Bagdad, Irak"),
    "muscat": (23.5880, 58.3829, "Mascate, Oman"),
    "dakar": (14.7167, -17.4677, "Dakar, Sénégal"),
    "abidjan": (5.3600, -4.0083, "Abidjan, Côte d'Ivoire"),
    "bamako": (12.6392, -8.0029, "Bamako, Mali"),
    "ouagadougou": (12.3714, -1.5197, "Ouagadougou, Burkina Faso"),
    "niamey": (13.5127, 2.1126, "Niamey, Niger"),
    "ndjamena": (12.1348, 15.0557, "N'Djamena, Tchad"),
    "conakry": (9.6412, -13.5784, "Conakry, Guinée"),
    "lome": (6.1725, 1.2314, "Lomé, Togo"),
    "cotonou": (6.3703, 2.3912, "Cotonou, Bénin"),
    "yaounde": (3.8480, 11.5021, "Yaoundé, Cameroun"),
    "yaoundé": (3.8480, 11.5021, "Yaoundé, Cameroun"),
    "douala": (4.0483, 9.7043, "Douala, Cameroun"),
    "libreville": (0.4162, 9.4673, "Libreville, Gabon"),
    "brazzaville": (-4.2634, 15.2429, "Brazzaville, Congo"),
    "kinshasa": (-4.4419, 15.2663, "Kinshasa, RDC"),
    "luanda": (-8.8390, 13.2894, "Luanda, Angola"),
    "nairobi": (-1.2921, 36.8219, "Nairobi, Kenya"),
    "lagos": (6.5244, 3.3792, "Lagos, Nigeria"),
    "accra": (5.6037, -0.1870, "Accra, Ghana"),
    "addis ababa": (9.0192, 38.7525, "Addis-Abeba, Éthiopie"),
    "dar es salaam": (-6.7924, 39.2083, "Dar es Salaam, Tanzanie"),
    "kampala": (0.3476, 32.5825, "Kampala, Ouganda"),
    "kigali": (-1.9403, 29.8739, "Kigali, Rwanda"),
    "maputo": (-25.9692, 32.5732, "Maputo, Mozambique"),
    "antananarivo": (-18.8792, 47.5079, "Antananarivo, Madagascar"),
    "paris": (48.8566, 2.3522, "Paris, France"),
    "lyon": (45.7640, 4.8357, "Lyon, France"),
    "marseille": (43.2965, 5.3698, "Marseille, France"),
    "toulouse": (43.6047, 1.4442, "Toulouse, France"),
    "bordeaux": (44.8378, -0.5792, "Bordeaux, France"),
    "lille": (50.6292, 3.0573, "Lille, France"),
    "nantes": (47.2184, -1.5536, "Nantes, France"),
    "strasbourg": (48.5734, 7.7521, "Strasbourg, France"),
    "montpellier": (43.6108, 3.8767, "Montpellier, France"),
    "nice": (43.7102, 7.2620, "Nice, France"),
    "bruxelles": (50.8503, 4.3517, "Bruxelles, Belgique"),
    "brussels": (50.8503, 4.3517, "Bruxelles, Belgique"),
    "genève": (46.2044, 6.1432, "Genève, Suisse"),
    "geneva": (46.2044, 6.1432, "Genève, Suisse"),
    "montréal": (45.5017, -73.5673, "Montréal, Canada"),
    "montreal": (45.5017, -73.5673, "Montréal, Canada"),
    "istanbul": (41.0082, 28.9784, "Istanbul, Turquie"),
    "ankara": (39.9334, 32.8597, "Ankara, Turquie"),
}

# ============================================================
# MAPPING TYPES DE COMMERCE → TAGS OVERPASS
# ============================================================
BUSINESS_TYPE_MAPPING = {
    # Restauration
    "restaurant": {"amenity": "restaurant"},
    "restaurants": {"amenity": "restaurant"},
    "café": {"amenity": "cafe"},
    "cafe": {"amenity": "cafe"},
    "fast food": {"amenity": "fast_food"},
    "fast_food": {"amenity": "fast_food"},
    "pizzeria": {"amenity": "restaurant", "cuisine": "pizza"},
    "pizzéria": {"amenity": "restaurant", "cuisine": "pizza"},
    "boulangerie": {"shop": "bakery"},
    "boulangeries": {"shop": "bakery"},
    "pâtisserie": {"shop": "pastry"},
    "patisserie": {"shop": "pastry"},
    "boucherie": {"shop": "butcher"},
    "traiteur": {"shop": "deli"},
    "bar": {"amenity": "bar"},
    "pub": {"amenity": "pub"},
    "brasserie": {"amenity": "restaurant"},
    "snack": {"amenity": "fast_food"},
    "glacier": {"amenity": "ice_cream"},
    "thé": {"amenity": "cafe"},
    "salon de thé": {"amenity": "cafe"},

    # Hébergement
    "hôtel": {"tourism": "hotel"},
    "hotel": {"tourism": "hotel"},
    "hôtels": {"tourism": "hotel"},
    "riad": {"tourism": "guest_house"},
    "auberge": {"tourism": "guest_house"},
    "guest house": {"tourism": "guest_house"},
    "hostel": {"tourism": "hostel"},
    "motel": {"tourism": "motel"},
    "camping": {"tourism": "camp_site"},

    # Santé
    "pharmacie": {"amenity": "pharmacy"},
    "pharmacies": {"amenity": "pharmacy"},
    "pharmacy": {"amenity": "pharmacy"},
    "hôpital": {"amenity": "hospital"},
    "hopital": {"amenity": "hospital"},
    "clinique": {"amenity": "clinic"},
    "dentiste": {"amenity": "dentist"},
    "médecin": {"amenity": "doctors"},
    "medecin": {"amenity": "doctors"},
    "vétérinaire": {"amenity": "veterinary"},
    "veterinaire": {"amenity": "veterinary"},
    "opticien": {"shop": "optician"},
    "laboratoire": {"healthcare": "laboratory"},

    # Beauté / Bien-être
    "coiffeur": {"shop": "hairdresser"},
    "coiffure": {"shop": "hairdresser"},
    "salon de coiffure": {"shop": "hairdresser"},
    "barbier": {"shop": "hairdresser"},
    "esthétique": {"shop": "beauty"},
    "esthetique": {"shop": "beauty"},
    "spa": {"leisure": "spa"},
    "massage": {"leisure": "spa"},
    "beauté": {"shop": "beauty"},
    "beaute": {"shop": "beauty"},
    "nail bar": {"shop": "beauty"},
    "ongles": {"shop": "beauty"},

    # Commerce
    "supermarché": {"shop": "supermarket"},
    "supermarche": {"shop": "supermarket"},
    "superette": {"shop": "convenience"},
    "épicerie": {"shop": "convenience"},
    "epicerie": {"shop": "convenience"},
    "magasin": {"shop": "yes"},
    "boutique": {"shop": "yes"},
    "vêtements": {"shop": "clothes"},
    "vetements": {"shop": "clothes"},
    "chaussures": {"shop": "shoes"},
    "bijouterie": {"shop": "jewelry"},
    "fleuriste": {"shop": "florist"},
    "librairie": {"shop": "books"},
    "papeterie": {"shop": "stationery"},
    "quincaillerie": {"shop": "hardware"},
    "meubles": {"shop": "furniture"},
    "électronique": {"shop": "electronics"},
    "electronique": {"shop": "electronics"},
    "téléphone": {"shop": "mobile_phone"},
    "telephone": {"shop": "mobile_phone"},
    "informatique": {"shop": "computer"},
    "cosmétique": {"shop": "cosmetics"},
    "cosmetique": {"shop": "cosmetics"},
    "parfumerie": {"shop": "cosmetics"},

    # Services
    "banque": {"amenity": "bank"},
    "assurance": {"office": "insurance"},
    "immobilier": {"office": "estate_agent"},
    "agence immobilière": {"office": "estate_agent"},
    "agence de voyage": {"shop": "travel_agency"},
    "notaire": {"office": "notary"},
    "avocat": {"office": "lawyer"},
    "comptable": {"office": "accountant"},
    "laverie": {"shop": "laundry"},
    "pressing": {"shop": "dry_cleaning"},
    "auto-école": {"amenity": "driving_school"},
    "école": {"amenity": "school"},
    "ecole": {"amenity": "school"},
    "crèche": {"amenity": "kindergarten"},
    "creche": {"amenity": "kindergarten"},
    "salle de sport": {"leisure": "fitness_centre"},
    "fitness": {"leisure": "fitness_centre"},
    "gym": {"leisure": "fitness_centre"},
    "piscine": {"leisure": "swimming_pool"},

    # Automobile
    "garage": {"shop": "car_repair"},
    "mécanique": {"shop": "car_repair"},
    "mecanique": {"shop": "car_repair"},
    "carrosserie": {"shop": "car_repair"},
    "station-service": {"amenity": "fuel"},
    "station service": {"amenity": "fuel"},
    "essence": {"amenity": "fuel"},
    "lavage auto": {"amenity": "car_wash"},
    "parking": {"amenity": "parking"},
    "concessionnaire": {"shop": "car"},

    # Loisirs
    "cinéma": {"amenity": "cinema"},
    "cinema": {"amenity": "cinema"},
    "théâtre": {"amenity": "theatre"},
    "theatre": {"amenity": "theatre"},
    "musée": {"tourism": "museum"},
    "musee": {"tourism": "museum"},
    "parc": {"leisure": "park"},
    "jardin": {"leisure": "garden"},
    "zoo": {"tourism": "zoo"},
    "aquarium": {"tourism": "aquarium"},
    "bowling": {"leisure": "bowling_alley"},
    "salle de jeux": {"leisure": "amusement_arcade"},

    # Bâtiment / Artisanat
    "plombier": {"craft": "plumber"},
    "électricien": {"craft": "electrician"},
    "electricien": {"craft": "electrician"},
    "peintre": {"craft": "painter"},
    "menuisier": {"craft": "carpenter"},
    "serrurier": {"craft": "locksmith"},
    "déménagement": {"office": "moving_company"},
}

# Catégories OSM larges pour le niveau 2
OSM_CATEGORIES = {
    "commerce": "shop",
    "shop": "shop",
    "magasin": "shop",
    "boutique": "shop",
    "restaurant": "amenity",
    "nourriture": "amenity",
    "food": "amenity",
    "santé": "amenity",
    "sante": "amenity",
    "health": "amenity",
    "éducation": "amenity",
    "education": "amenity",
    "loisir": "leisure",
    "loisirs": "leisure",
    "tourisme": "tourism",
    "tourism": "tourism",
    "bureau": "office",
    "office": "office",
    "artisan": "craft",
    "craft": "craft",
}

# ============================================================
# SERVEURS OVERPASS (5 serveurs + retry)
# ============================================================
OVERPASS_SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.nchc.org.tw/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]


# ============================================================
# GEOCODING
# ============================================================
async def geocode_city(city: str) -> tuple:
    """Géocode une ville avec fallback multi-niveaux."""
    city_clean = city.strip()
    city_lower = city_clean.lower()

    if city_lower in MENA_CITIES:
        lat, lon, name = MENA_CITIES[city_lower]
        print(f"✅ Geocoding dictionnaire: {name} ({lat}, {lon})")
        return lat, lon, name

    variants = [
        city_clean,
        f"{city_clean}, Morocco",
        f"{city_clean}, Maroc",
        f"{city_clean}, France",
        f"{city_clean}, Tunisia",
        f"{city_clean}, Algeria",
    ]

    for variant in variants:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": variant, "format": "json", "limit": 1},
                    headers={"User-Agent": "LeadRadar/1.0"},
                )
                data = resp.json()
                if data and len(data) > 0:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    name = data[0].get("display_name", city_clean)
                    print(f"✅ Geocoding Nominatim: {name} ({lat}, {lon})")
                    return lat, lon, name
        except Exception as e:
            print(f"⚠️ Nominatim '{variant}' échoué: {e}")
            continue

        import asyncio
        await asyncio.sleep(1.1)

    print(f"❌ Geocoding échoué pour '{city}'")
    return None, None, city_clean


# ============================================================
# CONSTRUCTION REQUÊTE OVERPASS (3 niveaux)
# ============================================================
def _build_overpass_query(lat: float, lon: float, radius: int, business_type: str) -> str:
    bt = business_type.strip().lower()

    if bt in BUSINESS_TYPE_MAPPING:
        tags = BUSINESS_TYPE_MAPPING[bt]
        tag_filters = ""
        for key, value in tags.items():
            tag_filters += f'["{key}"="{value}"]'
        query = f"""
        [out:json][timeout:25];
        (
          node{tag_filters}(around:{radius},{lat},{lon});
          way{tag_filters}(around:{radius},{lat},{lon});
          relation{tag_filters}(around:{radius},{lat},{lon});
        );
        out center body 200;
        """
        print(f"🔍 Overpass niveau 1 (mapping): {bt} → {tags}")
        return query

    if bt in OSM_CATEGORIES:
        osm_key = OSM_CATEGORIES[bt]
        query = f"""
        [out:json][timeout:25];
        (
          node["{osm_key}"](around:{radius},{lat},{lon});
          way["{osm_key}"](around:{radius},{lat},{lon});
          relation["{osm_key}"](around:{radius},{lat},{lon});
        );
        out center body 200;
        """
        print(f"🔍 Overpass niveau 2 (catégorie): {bt} → [{osm_key}]")
        return query

    safe_name = bt.replace('"', '\\"')
    query = f"""
    [out:json][timeout:25];
    (
      node["name"~"{safe_name}",i](around:{radius},{lat},{lon});
      way["name"~"{safe_name}",i](around:{radius},{lat},{lon});
      relation["name"~"{safe_name}",i](around:{radius},{lat},{lon});
      node["amenity"~"{safe_name}",i](around:{radius},{lat},{lon});
      way["amenity"~"{safe_name}",i](around:{radius},{lat},{lon});
      node["shop"~"{safe_name}",i](around:{radius},{lat},{lon});
      way["shop"~"{safe_name}",i](around:{radius},{lat},{lon});
    );
    out center body 200;
    """
    print(f"🔍 Overpass niveau 3 (libre): regex '{safe_name}'")
    return query


# ============================================================
# PARSING RÉSULTATS OVERPASS
# ============================================================
def _parse_overpass_results(data: dict, business_type: str) -> list:
    results = []
    elements = data.get("elements", [])

    for el in elements:
        tags = el.get("tags", {})
        if not tags.get("name"):
            continue

        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")

        addr_parts = []
        if tags.get("addr:street"):
            addr_parts.append(tags["addr:street"])
        if tags.get("addr:housenumber"):
            addr_parts.append(tags["addr:housenumber"])
        if tags.get("addr:city"):
            addr_parts.append(tags["addr:city"])
        address = ", ".join(addr_parts) if addr_parts else ""

        phone = tags.get("phone") or tags.get("contact:phone") or ""
        website = tags.get("website") or tags.get("contact:website") or ""
        if website and not website.startswith("http"):
            website = "https://" + website
        email = tags.get("email") or tags.get("contact:email") or ""
        opening_hours = tags.get("opening_hours", "")
        description = tags.get("description") or tags.get("note") or ""
        google_maps = ""
        if lat and lon:
            google_maps = f"https://www.google.com/maps?q={lat},{lon}"
        detected_type = (
            tags.get("amenity") or tags.get("shop") or tags.get("tourism")
            or tags.get("leisure") or tags.get("office") or tags.get("craft")
            or business_type
        )

        results.append({
            "name": tags["name"],
            "address": address,
            "phone": phone,
            "website": website,
            "email": email,
            "lat": lat,
            "lon": lon,
            "business_type": detected_type,
            "opening_hours": opening_hours,
            "description": description,
            "google_maps": google_maps,
        })

    return results



# ============================================================
# FALLBACK NOMINATIM (quand Overpass est down)
# ============================================================
async def _search_nominatim_fallback(city: str, business_type: str) -> dict:
    """Fallback via Nominatim (meme base OSM qu Overpass)."""
    import urllib.parse
    query = f"{business_type} in {city}"
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(query)}&format=json&limit=50&addressdetails=1&countrycodes=ma,tn,dz,eg,fr,sn,ci"
    print(f"🗺️ Fallback Nominatim: {query}")
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers={"User-Agent": "LeadRadar/1.0"})
            if resp.status_code != 200:
                print(f"⚠️ Nominatim HTTP {resp.status_code}")
                return {"results": [], "total": 0, "source": "nominatim_failed"}
            data = resp.json()
            results = []
            for item in data:
                name = item.get("name", "")
                if not name:
                    name = item.get("display_name", "").split(",")[0]
                if not name:
                    continue
                addr = item.get("address", {})
                address_parts = []
                for k in ["road", "house_number", "city", "town", "village"]:
                    if addr.get(k):
                        address_parts.append(addr[k])
                address = ", ".join(address_parts)
                lat = float(item.get("lat", 0))
                lon = float(item.get("lon", 0))
                osm_type = item.get("type", business_type)
                phone = addr.get("phone", "")
                website = addr.get("website", "")
                results.append({
                    "name": name,
                    "address": address,
                    "phone": phone,
                    "website": website,
                    "email": "",
                    "lat": lat,
                    "lon": lon,
                    "business_type": osm_type,
                    "opening_hours": "",
                    "description": item.get("display_name", ""),
                    "google_maps": f"https://www.google.com/maps?q={lat},{lon}" if lat else "",
                })
            print(f"✅ {len(results)} resultats depuis Nominatim")
            return {"results": results, "total": len(results), "source": "Nominatim (fallback)"}
    except Exception as e:
        print(f"❌ Nominatim echoue: {e}")
        return {"results": [], "total": 0, "source": "all_sources_failed"}


# ============================================================
# FONCTION PRINCIPALE (avec retry + 5 serveurs)
# ============================================================
async def search_businesses(city: str, business_type: str, radius: int = 5000) -> dict:
    """Recherche des commerces via Overpass avec 5 serveurs et retry."""
    import asyncio

    lat, lon, city_name = await geocode_city(city)
    if not lat or not lon:
        return {"results": [], "total": 0, "source": "geocoding_failed"}

    query = _build_overpass_query(lat, lon, radius, business_type)

    # 2 tours complets de tous les serveurs
    for tour in range(1):
        for server_url in OVERPASS_SERVERS:
            try:
                print(f"📡 Essai: {server_url.split('/')[2]} (tour {tour+1})")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        server_url,
                        data={"data": query},
                        headers={"User-Agent": "LeadRadar/1.0"},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results = _parse_overpass_results(data, business_type)
                        server_name = server_url.split("/")[2]
                        print(f"✅ {len(results)} résultats depuis {server_name}")
                        return {
                            "results": results,
                            "total": len(results),
                            "source": f"Overpass ({server_name})",
                        }
                    else:
                        print(f"⚠️ HTTP {resp.status_code}")
            except httpx.TimeoutException:
                print(f"⚠️ Timeout")
            except Exception as e:
                print(f"⚠️ Erreur: {str(e)[:80]}")

            # Petite pause entre serveurs
            await asyncio.sleep(2)

    print("❌ Tous les serveurs Overpass ont échoué après 2 tours")
    print("🔄 Activation du fallback Nominatim...")
    return await _search_nominatim_fallback(city, business_type)