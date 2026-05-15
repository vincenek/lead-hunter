"""
Lead Hunter — OpenStreetMap Overpass API scraper.
No API key needed. Bounding boxes hardcoded for reliability.
"""
import random
import time
import hashlib
import os

import requests
from requests import RequestException

OVERPASS_URLS = (
    'https://overpass-api.de/api/interpreter',
    'http://overpass-api.de/api/interpreter',
)
HEADERS = {
    'User-Agent': 'LeadHunterApp/1.0 (personal lead generation tool)',
    'Accept': 'application/json',
}
OVERPASS_QUERY_TIMEOUT = int(os.environ.get('OVERPASS_QUERY_TIMEOUT', '20'))
OVERPASS_REQUEST_TIMEOUT = int(os.environ.get('OVERPASS_REQUEST_TIMEOUT', '25'))
CITY_RESULT_LIMIT = int(os.environ.get('CITY_RESULT_LIMIT', '35'))
SEARCH_TARGET_LEADS = int(os.environ.get('SEARCH_TARGET_LEADS', '25'))
IS_RENDER = bool(os.environ.get('RENDER'))
PUBLIC_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com', 'live.com', 'icloud.com',
    'aol.com', 'proton.me', 'protonmail.com', 'gmx.com', 'msn.com', 'me.com',
    'btinternet.com', 'googlemail.com', 'ymail.com',
}

# Bounding boxes: (south, north, west, east)
CITY_BBOXES = {
    'London':       (51.28,  51.69,  -0.51,   0.33),
    'Manchester':   (53.34,  53.55,  -2.35,  -2.10),
    'Birmingham':   (52.38,  52.57,  -1.97,  -1.74),
    'Leeds':        (53.72,  53.88,  -1.72,  -1.44),
    'Glasgow':      (55.79,  55.91,  -4.38,  -4.10),
    'Liverpool':    (53.32,  53.49,  -3.04,  -2.83),
    'Bristol':      (51.39,  51.52,  -2.68,  -2.51),
    'Sheffield':    (53.32,  53.46,  -1.60,  -1.34),
    'Edinburgh':    (55.87,  56.00,  -3.35,  -3.08),
    'Cardiff':      (51.45,  51.54,  -3.24,  -3.11),
    'Leicester':    (52.58,  52.68,  -1.20,  -1.06),
    'Nottingham':   (52.89,  53.00,  -1.22,  -1.10),
    'Newcastle':    (54.94,  55.04,  -1.72,  -1.56),
    'Coventry':     (52.37,  52.45,  -1.57,  -1.46),
    'New York':     (40.49,  40.91, -74.26, -73.70),
    'Los Angeles':  (33.70,  34.34,-118.67,-117.99),
    'Chicago':      (41.64,  42.02, -87.94, -87.52),
    'Houston':      (29.52,  30.11, -95.79, -95.01),
    'Phoenix':      (33.29,  33.91,-112.33,-111.93),
    'Philadelphia': (39.86,  40.14, -75.28, -74.95),
    'San Antonio':  (29.19,  29.74, -98.81, -98.25),
    'San Diego':    (32.53,  32.97,-117.30,-116.91),
    'Dallas':       (32.62,  33.02, -97.04, -96.55),
    'Austin':       (30.09,  30.52, -97.99, -97.56),
    'Jacksonville': (30.10,  30.57, -82.00, -81.39),
    'Fort Worth':   (32.55,  32.90, -97.54, -97.08),
    'Toronto':      (43.58,  43.86, -79.64, -79.12),
    'Vancouver':    (49.19,  49.36,-123.27,-122.99),
    'Montreal':     (45.41,  45.70, -73.98, -73.47),
    'Calgary':      (50.84,  51.18,-114.32,-113.86),
    'Edmonton':     (53.39,  53.71,-113.72,-113.27),
    'Ottawa':       (45.25,  45.53, -76.00, -75.48),
    'Winnipeg':     (49.76,  49.97, -97.32, -96.97),
    'Sydney':      (-34.17, -33.58, 150.52, 151.34),
    'Melbourne':   (-38.25, -37.57, 144.44, 145.44),
    'Brisbane':    (-27.77, -27.27, 152.67, 153.22),
    'Perth':       (-32.14, -31.62, 115.67, 116.10),
    'Adelaide':    (-35.19, -34.75, 138.46, 138.73),
    'Gold Coast':  (-28.17, -27.92, 153.27, 153.55),
    'Canberra':    (-35.49, -35.15, 148.99, 149.26),
}

REGIONS = {
    'Worldwide': [
        ('London', 'UK'), ('New York', 'USA'), ('Manchester', 'UK'),
        ('Los Angeles', 'USA'), ('Toronto', 'Canada'), ('Sydney', 'Australia'),
        ('Chicago', 'USA'), ('Birmingham', 'UK'), ('Melbourne', 'Australia'),
        ('Houston', 'USA'), ('Vancouver', 'Canada'), ('Leeds', 'UK'),
    ],
    'UK': [
        ('London', 'UK'), ('Manchester', 'UK'), ('Birmingham', 'UK'),
        ('Leeds', 'UK'), ('Glasgow', 'UK'), ('Liverpool', 'UK'),
        ('Bristol', 'UK'), ('Sheffield', 'UK'), ('Edinburgh', 'UK'),
        ('Cardiff', 'UK'), ('Leicester', 'UK'), ('Nottingham', 'UK'),
        ('Newcastle', 'UK'), ('Coventry', 'UK'),
    ],
    'USA': [
        ('New York', 'USA'), ('Los Angeles', 'USA'), ('Chicago', 'USA'),
        ('Houston', 'USA'), ('Phoenix', 'USA'), ('Philadelphia', 'USA'),
        ('San Antonio', 'USA'), ('San Diego', 'USA'), ('Dallas', 'USA'),
        ('Austin', 'USA'), ('Jacksonville', 'USA'), ('Fort Worth', 'USA'),
    ],
    'Canada': [
        ('Toronto', 'Canada'), ('Vancouver', 'Canada'), ('Montreal', 'Canada'),
        ('Calgary', 'Canada'), ('Edmonton', 'Canada'), ('Ottawa', 'Canada'),
        ('Winnipeg', 'Canada'),
    ],
    'Australia': [
        ('Sydney', 'Australia'), ('Melbourne', 'Australia'), ('Brisbane', 'Australia'),
        ('Perth', 'Australia'), ('Adelaide', 'Australia'), ('Gold Coast', 'Australia'),
        ('Canberra', 'Australia'),
    ],
}

CATEGORY_TAGS = {
    'restaurant':   [('amenity', 'restaurant')],
    'cafe':         [('amenity', 'cafe')],
    'coffee':       [('amenity', 'cafe')],
    'coffee shop':  [('amenity', 'cafe')],
    'bar':          [('amenity', 'bar')],
    'pub':          [('amenity', 'pub')],
    'fast food':    [('amenity', 'fast_food')],
    'takeaway':     [('amenity', 'fast_food')],
    'pizza':        [('amenity', 'restaurant')],
    'barber':       [('shop', 'hairdresser'), ('shop', 'barber')],
    'hair salon':   [('shop', 'hairdresser')],
    'hairdresser':  [('shop', 'hairdresser')],
    'beauty':       [('shop', 'beauty')],
    'beauty salon': [('shop', 'beauty')],
    'nail salon':   [('shop', 'beauty')],
    'gym':          [('leisure', 'fitness_centre')],
    'fitness':      [('leisure', 'fitness_centre')],
    'dentist':      [('amenity', 'dentist')],
    'doctor':       [('amenity', 'doctors')],
    'pharmacy':     [('amenity', 'pharmacy')],
    'hotel':        [('tourism', 'hotel')],
    'plumber':      [('craft', 'plumber')],
    'electrician':  [('craft', 'electrician')],
    'carpenter':    [('craft', 'carpenter')],
    'builder':      [('craft', 'construction')],
    'solicitor':    [('office', 'lawyer')],
    'lawyer':       [('office', 'lawyer')],
    'accountant':   [('office', 'accountant')],
    'estate agent': [('office', 'estate_agent')],
    'real estate':  [('office', 'estate_agent')],
    'florist':      [('shop', 'florist')],
    'bakery':       [('shop', 'bakery')],
    'butcher':      [('shop', 'butcher')],
    'optician':     [('shop', 'optician')],
    'tattoo':       [('shop', 'tattoo')],
    'garage':       [('shop', 'car_repair')],
    'car repair':   [('shop', 'car_repair')],
    'mechanic':     [('shop', 'car_repair')],
    'vet':          [('amenity', 'veterinary')],
    'pet shop':     [('shop', 'pet')],
    'clothes':      [('shop', 'clothes')],
    'jewellery':    [('shop', 'jewelry')],
    'jewelry':      [('shop', 'jewelry')],
    'laundry':      [('shop', 'laundry')],
}
BUSINESS_TYPES = tuple(sorted(CATEGORY_TAGS.keys()))


def _osm_tags(category):
    cat = category.lower().strip()
    if cat in CATEGORY_TAGS:
        return CATEGORY_TAGS[cat]
    for key, tags in CATEGORY_TAGS.items():
        if cat in key or key in cat:
            return tags
    return [('amenity', cat), ('shop', cat), ('craft', cat)]


def _get_bbox(city):
    return CITY_BBOXES.get(city)


def _normalize_website(url):
    if not url:
        return None
    cleaned = url.strip()
    if cleaned.startswith(('http://', 'https://')):
        return cleaned
    return f'https://{cleaned}'


def _email_domain(email):
    if not email or '@' not in email:
        return None
    return email.split('@', 1)[1].strip().lower()


def _is_public_email_domain(domain):
    return bool(domain) and domain in PUBLIC_EMAIL_DOMAINS


def _first_present(tags, keys):
    for key in keys:
        value = tags.get(key)
        if value:
            return value.strip()
    return None


def _lead_id(name, city, country, address, phone, email):
    base = '||'.join([
        (name or '').strip().lower(),
        (city or '').strip().lower(),
        (country or '').strip().lower(),
        (address or '').strip().lower(),
        (phone or '').strip().lower(),
        (email or '').strip().lower(),
    ])
    return hashlib.sha1(base.encode('utf-8')).hexdigest()[:16]


def _lead_priority(has_website, has_contact):
    if not has_website and has_contact:
        return 'HOT'
    if not has_website:
        return 'WARM'
    return 'LOW'


def _build_session():
    session = requests.Session()
    session.trust_env = False
    return session


def _fetch_overpass(query):
    last_error = None
    session = _build_session()

    try:
        for url in OVERPASS_URLS:
            try:
                resp = session.post(url, data={'data': query}, headers=HEADERS, timeout=OVERPASS_REQUEST_TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except ValueError as exc:
                last_error = f'invalid JSON from {url}: {exc}'
            except RequestException as exc:
                last_error = f'{url}: {exc}'
    finally:
        session.close()

    if last_error:
        print(f'[overpass] request failed: {last_error}')
    return None


def _search_city(category, city, country):
    bbox = _get_bbox(city)
    if not bbox:
        return []

    s, n, w, e = bbox
    bb = f'{s},{w},{n},{e}'
    leads = []
    seen = set()

    for tag_key, tag_val in _osm_tags(category)[:2]:
        query = (
            f'[out:json][timeout:{OVERPASS_QUERY_TIMEOUT}];'
            f'(node["{tag_key}"="{tag_val}"]({bb});'
            f'way["{tag_key}"="{tag_val}"]({bb});'
            f'relation["{tag_key}"="{tag_val}"]({bb}););'
            f'out body {CITY_RESULT_LIMIT};'
        )
        try:
            payload = _fetch_overpass(query)
            if not payload:
                continue

            elements = payload.get('elements', [])
            print(f'[overpass] {city}: {len(elements)} businesses found')

            for el in elements:
                t = el.get('tags', {})
                name = t.get('name')
                phone = _first_present(t, ('phone', 'contact:phone', 'telephone', 'contact:mobile', 'mobile'))
                email = _first_present(t, ('email', 'contact:email'))
                website = _normalize_website(t.get('website') or t.get('contact:website') or t.get('url'))
                email_domain = _email_domain(email)
                website_source = 'osm' if website else None
                if not website and email_domain and not _is_public_email_domain(email_domain):
                    website = f'https://{email_domain}'
                    website_source = 'email_domain'
                parts = [t.get(k) for k in ('addr:housenumber', 'addr:street', 'addr:city', 'addr:postcode') if t.get(k)]
                address = ', '.join(parts) or None
                dedupe_key = (
                    name.lower().strip() if name else '',
                    city.lower().strip(),
                    (address or '').lower().strip(),
                    (phone or '').strip(),
                )

                if not name or dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                has_website = bool(website)
                has_contact = bool(phone or email)
                leads.append({
                    'lead_id':     _lead_id(name, city, country, address, phone, email),
                    'name':        name,
                    'phone':       phone,
                    'email':       email,
                    'email_domain': email_domain,
                    'website':     website,
                    'website_source': website_source,
                    'has_website': has_website,
                    'has_contact': has_contact,
                    'needs_website': not has_website,
                    'address':     address,
                    'city':        city,
                    'country':     country,
                    'priority':    _lead_priority(has_website, has_contact),
                    'profile_link': f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}" if el.get('type') and el.get('id') else None,
                    'source':      'OpenStreetMap',
                })

                if len(leads) >= CITY_RESULT_LIMIT:
                    return leads

        except Exception as ex:
            print(f'[overpass] {city}: {ex}')

        time.sleep(0.35 if IS_RENDER else 1)

    return leads


def search_region(category, region, max_cities=6):
    cities = REGIONS.get(region, REGIONS['Worldwide'])[:max_cities]
    all_leads = []
    seen_global = set()

    for city, country in cities:
        print(f'[search] Scanning {city}, {country}...')
        for lead in _search_city(category, city, country):
            key = (
                (lead.get('name') or '').lower().strip(),
                (lead.get('city') or '').lower().strip(),
                (lead.get('address') or '').lower().strip(),
            )
            if key and key not in seen_global:
                seen_global.add(key)
                all_leads.append(lead)

        hot_count = sum(1 for lead in all_leads if lead.get('priority') == 'HOT')
        if hot_count >= SEARCH_TARGET_LEADS:
            break

        time.sleep(random.uniform(0.15, 0.35) if IS_RENDER else random.uniform(0.5, 1.0))

    priority_order = {'HOT': 0, 'WARM': 1, 'LOW': 2}
    all_leads.sort(
        key=lambda x: (
            priority_order.get(x['priority'], 9),
            0 if x.get('email') else 1,
            0 if x.get('phone') else 1,
            x.get('name') or '',
        )
    )
    return all_leads
